"""Semantic validation for the Configuration Wrapping Framework."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Spec
    from .types import Errors


def semantic_validate(spec: Spec, strict: bool = False) -> Errors:
    """
    Perform semantic validation on a specification.

    Args:
        spec: The specification to validate
        strict: Whether to perform strict validation

    Returns:
        A list of validation errors, empty if valid
    """
    errors = []

    # Validate provider IDs are unique
    errors.extend(validate_unique_provider_ids(spec))

    # Validate injector names are unique
    errors.extend(validate_unique_injector_names(spec))

    # Validate alias syntax
    errors.extend(validate_alias_syntax(spec))

    # Validate positional ordering
    errors.extend(validate_positional_ordering(spec))

    # Additional strict validations
    if strict:
        errors.extend(validate_strict_rules(spec))

    return errors


def validate_unique_provider_ids(spec: Spec) -> Errors:
    """Validate that provider IDs are unique."""
    errors = []
    seen_ids = set()

    for provider in spec.configuration_providers:
        if provider.id in seen_ids:
            errors.append(f"Duplicate provider ID: '{provider.id}'")
        else:
            seen_ids.add(provider.id)

    return errors


def validate_unique_injector_names(spec: Spec) -> Errors:
    """Validate that injector names are unique."""
    errors = []
    seen_names = set()

    for injector in spec.configuration_injectors:
        if injector.name in seen_names:
            errors.append(f"Duplicate injector name: '{injector.name}'")
        else:
            seen_names.add(injector.name)

    return errors


def validate_alias_syntax(spec: Spec) -> Errors:
    """
    Validate alias syntax for injectors.

    Rules:
    - env_var aliases should be valid environment variable names (uppercase, underscores)
    - named aliases should start with -- or -
    """
    errors = []
    env_var_pattern = re.compile(r"^[A-Z][A-Z0-9_]*$")

    for injector in spec.configuration_injectors:
        if injector.kind == "env_var":
            for alias in injector.aliases:
                if not env_var_pattern.match(alias):
                    errors.append(
                        f"Invalid env_var alias '{alias}' for injector '{injector.name}'. "
                        f"Must be uppercase with underscores and start with a letter."
                    )
        elif injector.kind == "named":
            for alias in injector.aliases:
                if not alias.startswith("-"):
                    errors.append(
                        f"Invalid named alias '{alias}' for injector '{injector.name}'. "
                        f"Must start with - or --"
                    )
                elif alias.startswith("--") and len(alias) <= 3:
                    errors.append(
                        f"Invalid named alias '{alias}' for injector '{injector.name}'. "
                        f"Long form (--) must have at least 2 characters after --"
                    )
                elif (
                    alias.startswith("-")
                    and not alias.startswith("--")
                    and len(alias) != 2
                ):
                    errors.append(
                        f"Invalid named alias '{alias}' for injector '{injector.name}'. "
                        f"Short form (-) must be exactly 2 characters"
                    )

    return errors


def validate_positional_ordering(spec: Spec) -> Errors:
    """
    Validate positional injector ordering.

    Rules:
    - All positional injectors must have an order value
    - Order values must be unique
    - Order values must be sequential (no gaps)
    """
    errors = []
    positional_injectors = [
        inj for inj in spec.configuration_injectors if inj.kind == "positional"
    ]

    # Check that all positional injectors have an order
    for injector in positional_injectors:
        if injector.order is None:
            errors.append(
                f"Positional injector '{injector.name}' must have an order value"
            )

    # Check for unique and sequential order values
    if positional_injectors:
        orders = [inj.order for inj in positional_injectors if inj.order is not None]
        unique_orders = set(orders)

        if len(orders) != len(unique_orders):
            errors.append("Positional injectors must have unique order values")

        if orders:
            min_order = min(orders)
            max_order = max(orders)
            expected_orders = set(range(min_order, max_order + 1))

            if unique_orders != expected_orders:
                errors.append(
                    f"Positional injectors must have sequential order values "
                    f"(found: {sorted(unique_orders)}, expected: {sorted(expected_orders)})"
                )

    return errors


def validate_strict_rules(spec: Spec) -> Errors:
    """
    Perform additional strict validations.

    Rules:
    - All injectors should have at least one alias
    - All injectors should have at least one source
    - File paths should exist (if possible to check)
    """
    errors = []

    for injector in spec.configuration_injectors:
        if not injector.aliases and injector.kind != "stdin_fragment":
            errors.append(f"Injector '{injector.name}' should have at least one alias")

        if not injector.sources:
            errors.append(f"Injector '{injector.name}' should have at least one source")

    return errors
