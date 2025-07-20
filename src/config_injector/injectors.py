"""Configuration injectors for injecting values into the target process."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import Injector
    from .token_engine import TokenEngine
    from .types import EnvMap, ProviderMaps, RuntimeContext


@dataclass
class ResolvedInjector:
    """Result of resolving an injector."""

    injector: Injector
    value: str | None
    applied_aliases: list[str]
    argv_segments: list[str]
    env_updates: EnvMap
    files_created: list[Path]
    skipped: bool
    errors: list[str]

    @property
    def is_sensitive(self) -> bool:
        """Return whether the value is sensitive."""
        return self.injector.sensitive

    @property
    def name(self) -> str:
        """Return the injector name for convenience."""
        return self.injector.name


def resolve_injector(
    injector: Injector,
    context: RuntimeContext,
    providers: ProviderMaps,
    token_engine: TokenEngine,
    spec: Any | None = None,
) -> ResolvedInjector:
    """Resolve an injector to its final value and injection plan."""

    # Check conditional injection
    if injector.when and not _evaluate_condition(
        injector.when, context, providers, token_engine
    ):
        return ResolvedInjector(
            injector=injector,
            value=None,
            applied_aliases=[],
            argv_segments=[],
            env_updates={},
            files_created=[],
            skipped=True,
            errors=[],
        )

    # Resolve value from sources
    value = _resolve_value(injector, context, providers, token_engine)

    # Apply type coercion
    if value is not None and injector.type:
        value, coercion_errors = _coerce_type(value, injector.type, injector)
    else:
        coercion_errors = []

    # Build injection plan
    applied_aliases = []
    argv_segments = []
    env_updates = {}
    files_created = []

    if value is not None and not coercion_errors:
        if injector.kind == "env_var":
            applied_aliases = injector.aliases
            for alias in applied_aliases:
                env_updates[alias] = value

        elif injector.kind == "named":
            if injector.aliases:
                applied_aliases = injector.aliases
                alias = injector.aliases[0]  # Use first alias
                if injector.connector == "=":
                    argv_segments.append(f"{alias}={value}")
                elif injector.connector == "space":
                    argv_segments.extend([alias, value])
                else:  # repeat
                    argv_segments.extend([alias, value])

        elif injector.kind == "positional":
            argv_segments.append(value)

        elif injector.kind == "file":
            file_path = _create_temp_file(value, injector)
            files_created.append(file_path)

            if injector.aliases:
                # Check if any alias is used as a token in the command
                alias_used_as_token = False
                if spec and hasattr(spec, "target") and hasattr(spec.target, "command"):
                    command_str = " ".join(spec.target.command)
                    for alias in injector.aliases:
                        if f"${{{alias}}}" in command_str:
                            alias_used_as_token = True
                            break

                if not alias_used_as_token:
                    # Inject file path as named argument only if not used as token
                    alias = injector.aliases[0]
                    if injector.connector == "=":
                        argv_segments.append(f"{alias}={file_path}")
                    else:
                        argv_segments.extend([alias, str(file_path)])
            else:
                # Inject file path as environment variable
                env_updates["TEMP_FILE"] = str(file_path)

        elif injector.kind == "stdin_fragment":
            # Store the value to be aggregated by the build process
            # The value will be appended to stdin_data in build_env_and_argv
            pass

    errors = coercion_errors

    return ResolvedInjector(
        injector=injector,
        value=value,
        applied_aliases=applied_aliases,
        argv_segments=argv_segments,
        env_updates=env_updates,
        files_created=files_created,
        skipped=False,
        errors=errors,
    )


def _resolve_value(
    injector: Injector,
    _context: RuntimeContext,
    _providers: ProviderMaps,
    token_engine: TokenEngine,
) -> str | None:
    """Resolve value from injector sources using first_non_empty precedence."""

    for source in injector.sources:
        # Expand tokens in source
        if isinstance(source, str):
            expanded_source = token_engine.expand(source)
        else:
            expanded_source = str(source)

        # Trim whitespace
        expanded_source = expanded_source.strip()

        # Check if non-empty
        if expanded_source:
            return expanded_source

    # No non-empty source found, use default
    if injector.default is not None:
        if isinstance(injector.default, str):
            return token_engine.expand(injector.default)
        return str(injector.default)

    # No default, check if required
    if injector.required:
        return None  # Will be handled as error by caller

    return None


def _evaluate_condition(
    condition: str,
    context: RuntimeContext,
    providers: ProviderMaps,
    token_engine: TokenEngine,
) -> bool:
    """Evaluate a conditional expression using the proper expression parser."""
    from .expression_parser import ExpressionError, evaluate_expression

    try:
        # Expand tokens in condition first
        expanded_condition = token_engine.expand(condition)

        # Build evaluation context from runtime context and providers
        eval_context = {}

        # Add environment variables to context
        eval_context.update(context.env)

        # Add provider values to context (flattened)
        for provider_id, provider_map in providers.items():
            for key, value in provider_map.items():
                # Use the key directly and also with provider prefix
                eval_context[key] = value
                eval_context[f"{provider_id}_{key}"] = value

        # Add runtime context values
        eval_context["HOME"] = str(context.home)
        eval_context["PID"] = str(context.pid)

        # Evaluate using the proper expression parser
        return evaluate_expression(expanded_condition, eval_context)

    except ExpressionError as e:
        # Log the error but fall back to the old simple evaluation for backward compatibility
        print(
            f"Warning: Expression evaluation failed, falling back to simple evaluation: {e}"
        )
        return _evaluate_condition_simple(expanded_condition)
    except Exception as e:
        # Unexpected error, fall back to simple evaluation
        print(
            f"Warning: Unexpected error in expression evaluation, falling back to simple evaluation: {e}"
        )
        return _evaluate_condition_simple(expanded_condition)


def _evaluate_condition_simple(expanded_condition: str) -> bool:
    """Simple fallback condition evaluation for backward compatibility."""
    # Simple boolean evaluation
    if expanded_condition.lower() in ("true", "1", "yes", "on"):
        return True
    elif expanded_condition.lower() in ("false", "0", "no", "off", ""):
        return False

    # Simple equality check: "value == expected"
    if " == " in expanded_condition:
        left, right = expanded_condition.split(" == ", 1)
        left = left.strip()
        right = right.strip()

        # Remove quotes from string literals
        if (
            right.startswith("'")
            and right.endswith("'")
            or right.startswith('"')
            and right.endswith('"')
        ):
            right = right[1:-1]

        return left == right

    # Simple inequality check: "value != expected"
    if " != " in expanded_condition:
        left, right = expanded_condition.split(" != ", 1)
        return left.strip() != right.strip()

    # Default: truthy evaluation
    return bool(expanded_condition)


def _coerce_type(
    value: str, target_type: str, injector: Injector | None = None
) -> tuple[str | None, list[str]]:
    """Coerce a string value to the target type."""
    errors: list[str] = []

    try:
        if target_type == "string":
            return value, errors

        elif target_type == "int":
            int(value)
            return value, errors

        elif target_type == "bool":
            # Normalize boolean values
            if value.lower() in ("true", "1", "yes", "on"):
                return "true", errors
            elif value.lower() in ("false", "0", "no", "off"):
                return "false", errors
            else:
                errors.append(f"Invalid boolean value: {value}")
                return None, errors

        elif target_type == "path":
            # Validate path existence
            path = Path(value)

            # Check if path exists
            if not path.exists():
                errors.append(f"Path does not exist: {value}")
                return None, errors

            # Return the normalized absolute path
            return str(path.resolve()), errors

        elif target_type == "list":
            # Use configurable delimiter, default to comma for backward compatibility
            delimiter = "," if injector is None else injector.delimiter
            items = [item.strip() for item in value.split(delimiter)]
            return json.dumps(items), errors

        elif target_type == "json":
            # Validate JSON
            json.loads(value)
            return value, errors

        else:
            errors.append(f"Unknown type: {target_type}")
            return None, errors

    except (ValueError, json.JSONDecodeError) as e:
        errors.append(f"Type coercion failed: {e}")
        return None, errors


def _create_temp_file(content: str, injector: Injector) -> Path:
    """Create a temporary file with the given content."""
    # Create temporary file
    suffix = ".tmp"
    if injector.type == "json" or (
        injector.type == "path" and (content.startswith("{") or content.startswith("["))
    ):
        suffix = ".json"

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    ) as temp_file:
        temp_file.write(content)
        temp_file.flush()
        return Path(temp_file.name)
