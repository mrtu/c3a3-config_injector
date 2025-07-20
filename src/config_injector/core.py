"""Core functionality for the Configuration Wrapping Framework."""

from __future__ import annotations

import os
import subprocess
import tempfile
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import yaml

from .models import Spec, Provider, Injector
from .types import EnvMap, ProviderMap, Argv, Errors, ProviderMaps, RuntimeContext
from .injectors import ResolvedInjector
from .streams import StreamWriter


@dataclass
class BuildResult:
    """Result of building environment and argv."""

    env: EnvMap
    argv: Argv
    stdin_data: Optional[bytes]
    files: List[Path]
    errors: Errors


@dataclass
class ExecutionResult:
    """Result of process execution."""

    exit_code: int
    duration_s: float
    stdout_path: Optional[Path]
    stderr_path: Optional[Path]


@dataclass
class DryRunReport:
    """Dry run report showing what would be executed."""

    providers: ProviderMaps
    resolved: Sequence[ResolvedInjector]
    build: BuildResult
    text_summary: str
    json_summary: dict


def load_spec(path: Path) -> Spec:
    """Load YAML specification from file."""
    data = yaml.safe_load(path.read_text())
    return Spec(**data)


def build_runtime_context(spec: Spec, *, env: Optional[EnvMap] = None, seq: int = 1) -> RuntimeContext:
    """Build runtime context for token expansion."""
    if env is None:
        env = dict(os.environ)

    return RuntimeContext(
        env=env,
        now=datetime.now(),
        pid=os.getpid(),
        home=str(Path.home()),
        seq=seq,
    )


def build_env_and_argv(
    spec: Spec,
    resolved: Sequence[ResolvedInjector],
    context: RuntimeContext,
) -> BuildResult:
    """Build final environment and argv from resolved injectors."""
    from .token_engine import TokenEngine
    from .providers import load_providers

    env = context.env.copy() if spec.env_passthrough else {}
    argv = spec.target.command.copy()
    stdin_data = None
    files = []
    errors = []

    # Collect positional injectors to be appended at the end
    positionals = [(r, r.injector.order or 0) for r in resolved if r.injector.kind == 'positional']
    positionals.sort(key=lambda x: x[1])  # Sort by order

    # Process other injectors
    for resolved_inj in resolved:
        if resolved_inj.injector.kind == 'positional':
            continue  # Already processed

        if resolved_inj.value is not None:
            if resolved_inj.injector.kind == 'env_var':
                for alias in resolved_inj.applied_aliases:
                    env[alias] = resolved_inj.value
            elif resolved_inj.injector.kind == 'named':
                argv.extend(resolved_inj.argv_segments)
            elif resolved_inj.injector.kind == 'file':
                argv.extend(resolved_inj.argv_segments)
            elif resolved_inj.injector.kind == 'stdin_fragment':
                if stdin_data is None:
                    stdin_data = b''
                stdin_data += resolved_inj.value.encode('utf-8')

        files.extend(resolved_inj.files_created)
        errors.extend(resolved_inj.errors)

    # Append positional arguments at the end
    for resolved_inj, _ in positionals:
        if resolved_inj.value is not None:
            argv.append(resolved_inj.value)
        files.extend(resolved_inj.files_created)
        errors.extend(resolved_inj.errors)

    # Expand tokens in the command arguments
    providers = load_providers(spec, context)
    token_engine = TokenEngine(context, providers)

    # Create alias-to-value mapping for direct token replacement
    alias_values = {}
    for resolved_inj in resolved:
        if resolved_inj.injector.kind == 'file' and resolved_inj.files_created:
            # Map aliases to file paths
            for alias in resolved_inj.injector.aliases:
                alias_values[alias] = str(resolved_inj.files_created[0])
        elif resolved_inj.value is not None:
            # Map aliases to values for other injector types
            for alias in resolved_inj.applied_aliases:
                alias_values[alias] = resolved_inj.value

    # Expand tokens in argv
    expanded_argv = []
    for arg in argv:
        expanded_arg = arg

        # First, handle alias-based tokens like ${--config}
        import re
        token_pattern = r'\$\{([^}]+)\}'
        matches = re.finditer(token_pattern, expanded_arg)

        for match in matches:
            token_content = match.group(1)
            if token_content in alias_values:
                # Replace alias token with its value
                expanded_arg = expanded_arg.replace(match.group(0), alias_values[token_content])

        # Then, handle standard tokens through token engine
        try:
            expanded_arg = token_engine.expand(expanded_arg)
        except Exception:
            # If expansion fails, keep the current value
            pass

        expanded_argv.append(expanded_arg)

    return BuildResult(
        env=env,
        argv=expanded_argv,
        stdin_data=stdin_data,
        files=files,
        errors=errors,
    )


def execute(spec: Spec, build: BuildResult, streams: StreamWriter, resolved: Optional[Sequence[ResolvedInjector]] = None, context: Optional[RuntimeContext] = None) -> ExecutionResult:
    """Execute the target process."""
    import time

    start_time = time.time()

    # Increment sequence counter if context is provided
    if context:
        context.seq += 1

    try:
        # Prepare working directory
        working_dir = Path(spec.target.working_dir).expanduser().resolve()
        working_dir.mkdir(parents=True, exist_ok=True)

        # Register sensitive values with the stream writer
        if resolved:
            sensitive_values = []
            for resolved_inj in resolved:
                if resolved_inj.is_sensitive and resolved_inj.value:
                    sensitive_values.append(resolved_inj.value)

            if sensitive_values:
                streams.register_sensitive_values(sensitive_values)

        # Determine shell execution
        if spec.target.shell and spec.target.shell != 'none':
            # Use shell execution
            cmd = ' '.join(build.argv)
            process = subprocess.Popen(
                cmd,
                shell=True,
                cwd=working_dir,
                env=build.env,
                stdin=subprocess.PIPE if build.stdin_data else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
            )
        else:
            # Use execve-style execution
            process = subprocess.Popen(
                build.argv,
                cwd=working_dir,
                env=build.env,
                stdin=subprocess.PIPE if build.stdin_data else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
            )

        # Send stdin data if provided
        if build.stdin_data:
            process.stdin.write(build.stdin_data)
            process.stdin.close()

        # Stream output
        stdout_data = b''
        stderr_data = b''

        while True:
            stdout_chunk = process.stdout.read(1024)
            stderr_chunk = process.stderr.read(1024)

            if stdout_chunk:
                stdout_data += stdout_chunk
                streams.write_stdout(stdout_chunk)

            if stderr_chunk:
                stderr_data += stderr_chunk
                streams.write_stderr(stderr_chunk)

            if not stdout_chunk and not stderr_chunk:
                break

        exit_code = process.wait()
        duration = time.time() - start_time

        # Clean up temporary files after execution
        for file_path in build.files:
            try:
                file_path.unlink(missing_ok=True)
            except Exception:
                pass

        return ExecutionResult(
            exit_code=exit_code,
            duration_s=duration,
            stdout_path=streams.stdout_config.path if streams.stdout_config else None,
            stderr_path=streams.stderr_config.path if streams.stderr_config else None,
        )

    except Exception as e:
        # Clean up temporary files on error
        for file_path in build.files:
            try:
                file_path.unlink(missing_ok=True)
            except Exception:
                pass
        raise


def dry_run(spec: Spec, context: RuntimeContext) -> DryRunReport:
    """Perform a dry run showing what would be executed."""
    # Import here to avoid circular imports
    from .providers import load_providers
    from .token_engine import TokenEngine
    from .injectors import resolve_injector

    # Increment sequence counter
    context.seq += 1

    # Load providers
    providers = load_providers(spec, context)

    # Create token engine
    token_engine = TokenEngine(context, providers)

    # Resolve injectors
    resolved = []
    for injector in spec.configuration_injectors:
        resolved_inj = resolve_injector(injector, context, providers, token_engine, spec)
        resolved.append(resolved_inj)

    # Build final result
    build = build_env_and_argv(spec, resolved, context)

    # Generate summary
    text_summary = _generate_text_summary(spec, providers, resolved, build)
    json_summary = _generate_json_summary(spec, providers, resolved, build)

    return DryRunReport(
        providers=providers,
        resolved=resolved,
        build=build,
        text_summary=text_summary,
        json_summary=json_summary,
    )


def _generate_text_summary(
    spec: Spec,
    providers: ProviderMaps,
    resolved: Sequence[ResolvedInjector],
    build: BuildResult,
) -> str:
    """Generate human-readable text summary."""
    from .types import mask_sensitive_value, MASKED_VALUE

    lines = []

    lines.append("=== Providers Loaded ===")
    for provider_id, provider_map in providers.items():
        masked_count = sum(1 for v in provider_map.values() if v == MASKED_VALUE)
        lines.append(f"{provider_id}: {len(provider_map)} keys (masked: {masked_count})")

    lines.append("\n=== Injection Plan ===")
    for resolved_inj in resolved:
        if resolved_inj.value is not None:
            value_display = mask_sensitive_value(resolved_inj.value, resolved_inj.is_sensitive)
            lines.append(f"{resolved_inj.injector.name} ({resolved_inj.injector.kind}) -> {value_display}")
        elif resolved_inj.skipped:
            lines.append(f"{resolved_inj.injector.name} -> SKIPPED")
        else:
            lines.append(f"{resolved_inj.injector.name} -> ERROR: {resolved_inj.errors}")

    lines.append("\n=== Final Invocation ===")
    lines.append(f"cd {spec.target.working_dir}")

    # Mask sensitive values in argv
    masked_argv = build.argv.copy()
    for i, arg in enumerate(masked_argv):
        # Check if this arg contains a sensitive value from any injector
        for resolved_inj in resolved:
            if resolved_inj.is_sensitive and resolved_inj.value and resolved_inj.value in arg:
                masked_argv[i] = arg.replace(resolved_inj.value, MASKED_VALUE)

    lines.append(f"argv: {masked_argv}")

    return "\n".join(lines)


def _generate_json_summary(
    spec: Spec,
    providers: ProviderMaps,
    resolved: Sequence[ResolvedInjector],
    build: BuildResult,
) -> dict:
    """Generate machine-readable JSON summary."""
    from .types import mask_sensitive_value, MASKED_VALUE

    # Mask sensitive values in argv
    masked_argv = build.argv.copy()
    for i, arg in enumerate(masked_argv):
        # Check if this arg contains a sensitive value from any injector
        for resolved_inj in resolved:
            if resolved_inj.is_sensitive and resolved_inj.value and resolved_inj.value in arg:
                masked_argv[i] = arg.replace(resolved_inj.value, MASKED_VALUE)

    return {
        "spec": {
            "version": spec.version,
            "working_dir": spec.target.working_dir,
            "command": spec.target.command,
        },
        "providers": {
            pid: {
                "count": len(pmap),
                "masked_count": sum(1 for v in pmap.values() if v == MASKED_VALUE),
            }
            for pid, pmap in providers.items()
        },
        "injections": [
            {
                "name": r.injector.name,
                "kind": r.injector.kind,
                "resolved": r.value is not None,
                "sensitive": r.is_sensitive,
                "value": mask_sensitive_value(r.value, r.is_sensitive) if r.value is not None else None,
                "skipped": r.skipped,
                "errors": r.errors,
            }
            for r in resolved
            if not r.skipped
        ],
        "build": {
            "env_keys": list(build.env.keys()),
            "argv": masked_argv,
            "files_created": len(build.files),
            "errors": build.errors,
        },
    }
