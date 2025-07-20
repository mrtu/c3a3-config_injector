"""Core functionality for the Configuration Wrapping Framework."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from .models import Spec
from .types import Argv, EnvMap, Errors, ProviderMaps, RuntimeContext

# Export RuntimeContext for other modules
__all__ = [
    "RuntimeContext",
    "BuildResult",
    "ExecutionResult",
    "DryRunReport",
    "load_spec",
    "build_runtime_context",
    "build_env_and_argv",
    "execute",
    "dry_run",
]

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .injectors import ResolvedInjector
    from .streams import StreamWriter
    from .token_engine import TokenEngine


@dataclass
class BuildResult:
    """Result of building environment and argv."""

    env: EnvMap
    argv: Argv
    stdin_data: bytes | None
    files: list[Path]
    errors: Errors


@dataclass
class ExecutionResult:
    """Result of process execution."""

    exit_code: int
    duration_s: float
    stdout_path: Path | None
    stderr_path: Path | None


@dataclass
class DryRunReport:
    """Dry run report showing what would be executed."""

    providers: ProviderMaps
    resolved: Sequence[ResolvedInjector]
    build: BuildResult
    text_summary: str
    json_summary: dict[str, Any]


def load_spec(path: Path) -> Spec:
    """Load YAML specification from file."""
    data = yaml.safe_load(path.read_text())
    return Spec(**data)


def build_runtime_context(*, env: EnvMap | None = None, seq: int = 1) -> RuntimeContext:
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
    token_engine: TokenEngine | None = None,
) -> BuildResult:
    """Build final environment and argv from resolved injectors."""

    env = context.env.copy() if spec.env_passthrough else {}

    # Create alias tokens mapping for file injectors
    alias_tokens = {}
    for resolved_inj in resolved:
        if resolved_inj.injector.kind == "file" and resolved_inj.files_created:
            for alias in resolved_inj.injector.aliases:
                alias_tokens[alias] = str(resolved_inj.files_created[0])

    # Create token engine with alias tokens if not provided
    if token_engine is None:
        from .providers import load_providers
        from .token_engine import TokenEngine

        providers = load_providers(spec, context)
        token_engine = TokenEngine(context, providers, alias_tokens)
    else:
        # Add alias tokens to existing token engine
        token_engine.alias_tokens.update(alias_tokens)

    # Expand tokens in command if token_engine is provided
    if token_engine:
        argv = [token_engine.expand(arg) for arg in spec.target.command]
    else:
        argv = spec.target.command.copy()

    stdin_data = None
    files = []
    errors = []

    # Collect positional injectors to be appended at the end
    positionals = [
        (r, r.injector.order or 0) for r in resolved if r.injector.kind == "positional"
    ]
    positionals.sort(key=lambda x: x[1])  # Sort by order

    # Process other injectors
    for resolved_inj in resolved:
        if resolved_inj.injector.kind == "positional":
            continue  # Handle positionals separately

        if resolved_inj.skipped:
            continue

        # Handle environment variables
        if resolved_inj.injector.kind == "env_var":
            for alias in resolved_inj.applied_aliases:
                env[alias] = resolved_inj.value or ""

        # Handle named arguments
        elif resolved_inj.injector.kind == "named":
            argv.extend(resolved_inj.argv_segments)

        # Handle file creation
        elif resolved_inj.injector.kind == "file":
            if resolved_inj.files_created:
                files.extend(resolved_inj.files_created)
            # Add file arguments to argv
            argv.extend(resolved_inj.argv_segments)

        # Handle stdin fragments
        elif resolved_inj.injector.kind == "stdin_fragment" and resolved_inj.value:
            if stdin_data is None:
                stdin_data = b""
            stdin_data += resolved_inj.value.encode("utf-8")

        # Collect errors
        errors.extend(resolved_inj.errors)

    # Append positional injectors in order
    for resolved_inj, _ in positionals:
        if not resolved_inj.skipped:
            argv.extend(resolved_inj.argv_segments)
            errors.extend(resolved_inj.errors)

    return BuildResult(
        env=env,
        argv=argv,
        stdin_data=stdin_data,
        files=files,
        errors=errors,
    )


def execute(
    spec: Spec,
    build: BuildResult,
    streams: StreamWriter,
    resolved: Sequence[ResolvedInjector] | None = None,
    context: RuntimeContext | None = None,
) -> ExecutionResult:
    """Execute the target command with the built environment and argv."""
    import time

    # Increment sequence counter if context is provided
    if context:
        context.seq += 1

    # Register sensitive values for masking
    if resolved:
        sensitive_values = []
        for r in resolved:
            if r.is_sensitive and r.value:
                sensitive_values.append(r.value)
        streams.register_sensitive_values(sensitive_values)

    # Change to working directory
    working_dir = Path(spec.target.working_dir)
    working_dir.mkdir(parents=True, exist_ok=True)

    # Prepare stdin
    stdin_pipe = None
    if build.stdin_data:
        stdin_pipe = subprocess.PIPE

    # Start timing
    start_time = time.time()

    # Execute the command
    try:
        process = subprocess.Popen(
            build.argv,
            cwd=working_dir,
            env=build.env,
            stdin=stdin_pipe,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,  # Use bytes for better stream handling
        )

        # Send stdin data if provided
        if build.stdin_data and stdin_pipe and process.stdin:
            process.stdin.write(build.stdin_data)
            process.stdin.close()

        # Read output streams
        stdout_data = b""
        stderr_data = b""

        while True:
            stdout_chunk = process.stdout.read(4096) if process.stdout else b""
            stderr_chunk = process.stderr.read(4096) if process.stderr else b""

            if stdout_chunk:
                stdout_data += stdout_chunk
                streams.write_stdout(stdout_chunk)

            if stderr_chunk:
                stderr_data += stderr_chunk
                streams.write_stderr(stderr_chunk)

            # Check if process has finished
            if process.poll() is not None:
                # Read any remaining output
                remaining_stdout = process.stdout.read() if process.stdout else b""
                remaining_stderr = process.stderr.read() if process.stderr else b""

                if remaining_stdout:
                    stdout_data += remaining_stdout
                    streams.write_stdout(remaining_stdout)

                if remaining_stderr:
                    stderr_data += remaining_stderr
                    streams.write_stderr(remaining_stderr)

                break

        # Wait for process to complete
        exit_code = process.wait()

    except Exception as e:
        # Handle execution errors
        exit_code = 1
        error_msg = f"Execution failed: {e}"
        stderr_data = error_msg.encode("utf-8")
        streams.write_stderr(stderr_data)

    finally:
        # Close process streams
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()

    # Calculate duration
    duration_s = time.time() - start_time

    # Save output to files if configured
    stdout_path = (
        streams.stdout_config.path
        if streams.stdout_config and streams.stdout_config.path
        else None
    )
    stderr_path = (
        streams.stderr_config.path
        if streams.stderr_config and streams.stderr_config.path
        else None
    )

    # Clean up temporary files created by file injectors
    if resolved:
        import contextlib

        for r in resolved:
            if hasattr(r, "files_created") and r.files_created:
                for file_path in r.files_created:
                    with contextlib.suppress(Exception):
                        file_path.unlink(missing_ok=True)

    return ExecutionResult(
        exit_code=exit_code,
        duration_s=duration_s,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )


def dry_run(spec: Spec, context: RuntimeContext) -> DryRunReport:
    """Perform a dry run to show what would be executed."""
    from .injectors import resolve_injector
    from .providers import load_providers
    from .token_engine import TokenEngine

    # Increment sequence counter
    context.seq += 1

    # Load providers
    providers = load_providers(spec, context)

    # Create token engine
    token_engine = TokenEngine(context, providers)

    # Resolve injectors
    resolved = []
    for injector in spec.configuration_injectors:
        resolved_inj = resolve_injector(
            injector, context, providers, token_engine, spec
        )
        resolved.append(resolved_inj)

    # Build final result
    build = build_env_and_argv(spec, resolved, context, token_engine)

    # Generate summaries
    text_summary = _generate_text_summary(providers, resolved, build)
    json_summary = _generate_json_summary(spec, providers, resolved, build)

    return DryRunReport(
        providers=providers,
        resolved=resolved,
        build=build,
        text_summary=text_summary,
        json_summary=json_summary,
    )


def _generate_text_summary(
    providers: ProviderMaps,
    resolved: Sequence[ResolvedInjector],
    build: BuildResult,
) -> str:
    """Generate a text summary of the dry run."""
    from .types import MASKED_VALUE

    lines = []
    if providers:
        lines.append("Providers Loaded")
    lines.append("Configuration Summary")
    lines.append("=" * 50)
    lines.append("")

    # Providers
    lines.append("Providers:")
    for provider_id, provider_map in providers.items():
        masked_count = sum(1 for v in provider_map.values() if v == MASKED_VALUE)
        if masked_count > 0:
            lines.append(
                f"  {provider_id}: {len(provider_map)} keys (masked: {masked_count})"
            )
        else:
            lines.append(f"  {provider_id}: {len(provider_map)} keys")
    lines.append("")

    # Injectors
    lines.append("Injection Plan")
    lines.append("Injectors:")
    for r in resolved:
        status = "SKIPPED" if r.skipped else "ACTIVE"
        if r.value is not None:
            # Mask sensitive values
            display_value = r.value
            if r.is_sensitive:
                display_value = MASKED_VALUE
            else:
                # Check if this value contains any sensitive values from other injectors
                for other_r in resolved:
                    if (
                        other_r.is_sensitive
                        and other_r.value
                        and other_r.value in display_value
                    ):
                        display_value = display_value.replace(
                            other_r.value, MASKED_VALUE
                        )
            lines.append(f"  {r.name}: {status} = {display_value}")
        else:
            lines.append(f"  {r.name}: {status}")
        if r.errors:
            for error in r.errors:
                lines.append(f"    ERROR: {error}")
    lines.append("")

    # Final Invocation
    lines.append("Final Invocation")
    lines.append(f"Working directory: {build.env.get('PWD', '') or ''}")

    # Mask sensitive values in command line
    masked_argv = build.argv.copy()
    for r in resolved:
        if r.is_sensitive and r.value:
            for i, arg in enumerate(masked_argv):
                if r.value in arg:
                    masked_argv[i] = arg.replace(r.value, MASKED_VALUE)

    lines.append(f"Command: {' '.join(masked_argv)}")
    lines.append(f"Environment: {len(build.env)} variables")
    lines.append("")

    # Files
    if build.files:
        lines.append("Files to be created:")
        for file_path in build.files:
            lines.append(f"  {file_path}")
        lines.append("")

    # Errors
    if build.errors:
        lines.append("Errors:")
        for error in build.errors:
            lines.append(f"  {error}")
        lines.append("")

    return "\n".join(lines)


def _generate_json_summary(
    spec: Spec,
    providers: ProviderMaps,
    resolved: Sequence[ResolvedInjector],
    build: BuildResult,
) -> dict[str, Any]:
    """Generate a JSON summary of the dry run."""
    from .types import MASKED_VALUE

    return {
        "spec": {
            "version": spec.version,
            "working_dir": spec.target.working_dir,
            "command": spec.target.command,
        },
        "providers": {
            provider_id: {
                "key_count": len(provider_map),
                "masked_count": sum(
                    1 for v in provider_map.values() if v == MASKED_VALUE
                ),
            }
            for provider_id, provider_map in providers.items()
        },
        "injections": [
            {
                "name": r.name,
                "kind": r.injector.kind,
                "skipped": r.skipped,
                "sensitive": r.is_sensitive,
                "value": MASKED_VALUE if r.is_sensitive and r.value else r.value,
                "resolved": not r.skipped,
                "errors": r.errors,
            }
            for r in resolved
            if not r.skipped  # Only include non-skipped injectors
        ],
        "build": {
            "env_count": len(build.env),
            "argv": build.argv,
            "file_count": len(build.files),
            "error_count": len(build.errors),
            "env_keys": list(build.env.keys()),
        },
    }
