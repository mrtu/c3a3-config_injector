"""Command-line interface for the Configuration Wrapping Framework."""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path  # noqa: TC003

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .core import build_runtime_context, dry_run, execute, load_spec
from .streams import StreamWriter, prepare_stream

app = typer.Typer(help="Configuration Wrapping Framework")
console = Console()


@app.command()
def run(
    spec_file: Path = typer.Argument(..., help="Path to YAML specification file"),
    dry_run_flag: bool = typer.Option(False, "--dry-run", help="Show what would be executed without running"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format (only with --dry-run)"),
    profile: str | None = typer.Option(None, "--profile", help="Profile to use"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Enable quiet mode (minimal output)"),
    env_passthrough: bool | None = typer.Option(None, "--env-passthrough/--no-env-passthrough", help="Override env_passthrough setting"),
    mask_defaults: bool | None = typer.Option(None, "--mask-defaults/--no-mask-defaults", help="Override mask_defaults setting"),
    strict: bool = typer.Option(False, "--strict", help="Enable strict validation"),
) -> None:
    """Run a configuration specification."""
    try:
        # Validate conflicting options
        if verbose and quiet:
            console.print("[red]Error: --verbose and --quiet cannot be used together[/red]")
            sys.exit(1)

        # Load specification
        spec = load_spec(spec_file)

        # Apply CLI overrides to spec
        if env_passthrough is not None:
            spec.env_passthrough = env_passthrough
        if mask_defaults is not None:
            spec.mask_defaults = mask_defaults

        # Apply profile if specified
        if profile:
            if spec.profiles and profile in spec.profiles:
                profile_config = spec.profiles[profile]
                if verbose and not quiet:
                    console.print(f"[blue]Applying profile: {profile}[/blue]")
                # Basic profile support - merge profile settings into spec
                # This is a simplified implementation for now
                for key, value in profile_config.items():
                    if hasattr(spec, key):
                        setattr(spec, key, value)
            else:
                if spec.profiles is None:
                    console.print(f"[yellow]Warning: No profiles defined in spec, ignoring --profile {profile}[/yellow]")
                else:
                    console.print(f"[red]Error: Profile '{profile}' not found in spec[/red]")
                    sys.exit(1)

        # Build runtime context
        context = build_runtime_context()

        # Perform validation if strict mode is enabled
        if strict:
            from .validation import semantic_validate
            semantic_errors = semantic_validate(spec, strict=True)
            if semantic_errors:
                console.print("[red]Strict validation failed:[/red]")
                for error in semantic_errors:
                    console.print(f"  [red]• {error}[/red]")
                sys.exit(1)

        if dry_run_flag:
            # Perform dry run
            report = dry_run(spec, context)

            if report.build.errors:
                console.print("[red]Configuration errors:[/red]")
                for error in report.build.errors:
                    console.print(f"  [red]• {error}[/red]")
                sys.exit(1)

            if json_output:
                import json
                console.print(json.dumps(report.json_summary, indent=2))
            else:
                if not quiet:
                    console.print(Panel(report.text_summary, title="Dry Run Report"))
                elif verbose:
                    console.print(report.text_summary)
        else:
            if json_output and not quiet:
                console.print("[yellow]Warning: --json flag is ignored without --dry-run[/yellow]")
            # Execute the specification
            _execute_spec(spec, context, verbose=verbose, quiet=quiet)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@app.command()
def validate(
    spec_file: Path = typer.Argument(..., help="Path to YAML specification file"),
    strict: bool = typer.Option(False, "--strict", help="Enable strict validation"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Enable quiet mode (minimal output)"),
) -> None:
    """Validate a configuration specification."""
    try:
        # Validate conflicting options
        if verbose and quiet:
            console.print("[red]Error: --verbose and --quiet cannot be used together[/red]")
            sys.exit(1)

        # Load specification (this will validate schema)
        spec = load_spec(spec_file)

        if verbose and not quiet:
            console.print(f"[blue]Loaded specification from {spec_file}[/blue]")
            console.print(f"Version: {spec.version}")
            console.print(f"Providers: {len(spec.configuration_providers)}")
            console.print(f"Injectors: {len(spec.configuration_injectors)}")

        # Build runtime context for semantic validation
        context = build_runtime_context()

        # Perform dry run to catch runtime issues
        if verbose and not quiet:
            console.print("[blue]Performing dry run validation...[/blue]")

        report = dry_run(spec, context)

        if report.build.errors:
            console.print("[red]Validation failed:[/red]")
            for error in report.build.errors:
                console.print(f"  [red]• {error}[/red]")
            sys.exit(1)

        # Perform semantic validation
        if verbose and not quiet:
            console.print("[blue]Performing semantic validation...[/blue]")

        from .validation import semantic_validate
        semantic_errors = semantic_validate(spec, strict=strict)

        if semantic_errors:
            console.print("[red]Semantic validation failed:[/red]")
            for error in semantic_errors:
                console.print(f"  [red]• {error}[/red]")
            sys.exit(1)

        if not quiet:
            if strict:
                console.print("[green]✓ Specification is valid (strict mode)[/green]")
            else:
                console.print("[green]✓ Specification is valid[/green]")

    except Exception as e:
        console.print(f"[red]Validation error: {e}[/red]")
        sys.exit(1)


@app.command()
def explain(
    spec_file: Path = typer.Argument(..., help="Path to YAML specification file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Enable quiet mode (minimal output)"),
) -> None:
    """Explain a configuration specification."""
    try:
        # Validate conflicting options
        if verbose and quiet:
            console.print("[red]Error: --verbose and --quiet cannot be used together[/red]")
            sys.exit(1)

        # Load specification
        spec = load_spec(spec_file)

        if verbose and not quiet:
            console.print(f"[blue]Loaded specification from {spec_file}[/blue]")

        # Build runtime context
        context = build_runtime_context()

        # Perform dry run
        report = dry_run(spec, context)

        # Display detailed explanation
        _display_explanation(spec, report)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@app.command()
def print_schema() -> None:
    """Print the JSON schema for specifications."""
    from .models import Spec

    # Generate schema
    schema = Spec.model_json_schema()

    import json
    console.print(json.dumps(schema, indent=2))


def _execute_spec(spec, context, verbose: bool = False, quiet: bool = False) -> None:
    """Execute a specification."""
    from .injectors import resolve_injector
    from .providers import load_providers
    from .token_engine import TokenEngine

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
    from .core import build_env_and_argv
    build = build_env_and_argv(spec, resolved, context)

    # Check for errors
    if build.errors:
        console.print("[red]Configuration errors:[/red]")
        for error in build.errors:
            console.print(f"  [red]• {error}[/red]")
        sys.exit(1)

    # Verbose output: show configuration details
    if verbose and not quiet:
        console.print("[blue]Configuration loaded successfully[/blue]")
        console.print(f"Providers: {len(providers)}")
        console.print(f"Injectors: {len(resolved)}")
        console.print(f"Working directory: {spec.target.working_dir}")
        console.print(f"Command: {' '.join(spec.target.command)}")

    # Prepare streams
    stdout_config = prepare_stream(spec.target.stdout, context, token_engine, spec)
    stderr_config = prepare_stream(spec.target.stderr, context, token_engine, spec)

    # Create stream writer
    streams = StreamWriter(stdout_config, stderr_config)

    try:
        # Execute with resolved injectors for masking sensitive values
        result = execute(spec, build, streams, resolved)

        # Display result based on verbosity
        if not quiet:
            console.print("\n[bold]Execution completed[/bold]")
            console.print(f"Exit code: {result.exit_code}")
            if verbose:
                console.print(f"Duration: {result.duration_s:.2f}s")

        if result.exit_code != 0:
            sys.exit(result.exit_code)

    finally:
        # Clean up
        streams.close()

        # Clean up temporary files
        for file_path in build.files:
            with contextlib.suppress(Exception):
                file_path.unlink(missing_ok=True)


def _display_explanation(spec, report) -> None:
    """Display detailed explanation of a specification."""
    # Providers table
    providers_table = Table(title="Configuration Providers")
    providers_table.add_column("ID", style="cyan")
    providers_table.add_column("Type", style="magenta")
    providers_table.add_column("Keys", style="green")
    providers_table.add_column("Masked", style="yellow")

    for provider_id, provider_map in report.providers.items():
        masked_count = sum(1 for v in provider_map.values() if v == "<masked>")
        providers_table.add_row(
            provider_id,
            "env" if provider_id == "env" else "dotenv" if "dotenv" in provider_id else "bws",
            str(len(provider_map)),
            str(masked_count),
        )

    console.print(providers_table)

    # Injectors table
    injectors_table = Table(title="Configuration Injectors")
    injectors_table.add_column("Name", style="cyan")
    injectors_table.add_column("Kind", style="magenta")
    injectors_table.add_column("Status", style="green")
    injectors_table.add_column("Value", style="yellow")

    for resolved_inj in report.resolved:
        if resolved_inj.value is not None:
            value_display = "<masked>" if resolved_inj.is_sensitive else resolved_inj.value
            status = "✓ Resolved"
        elif resolved_inj.skipped:
            value_display = "N/A"
            status = "⏭ Skipped"
        else:
            value_display = "N/A"
            status = "✗ Error"

        injectors_table.add_row(
            resolved_inj.injector.name,
            resolved_inj.injector.kind,
            status,
            value_display,
        )

    console.print(injectors_table)

    # Final invocation
    console.print("\n[bold]Final Command:[/bold]")
    console.print(f"Working directory: {spec.target.working_dir}")
    console.print(f"Command: {' '.join(report.build.argv)}")
    console.print(f"Environment variables: {len(report.build.env)}")


if __name__ == "__main__":
    app()
