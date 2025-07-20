"""Tests for the semantic validation module."""

import pytest

from config_injector.models import Injector, Provider, Spec, Target
from config_injector.validation import (
    semantic_validate,
    validate_alias_syntax,
    validate_positional_ordering,
    validate_strict_rules,
    validate_unique_injector_names,
    validate_unique_provider_ids,
)


def test_validate_unique_provider_ids():
    """Test validation of unique provider IDs."""
    # Create a spec with duplicate provider IDs
    spec = Spec(
        version="0.1",
        configuration_providers=[
            Provider(
                type="env",
                id="env",
                name="Test Environment",
                passthrough=True,
                filter_chain=[],
            ),
            Provider(
                type="dotenv",
                id="env",  # Duplicate ID
                name="Dotenv Provider",
                passthrough=False,
                filter_chain=[],
            ),
        ],
        configuration_injectors=[],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    errors = validate_unique_provider_ids(spec)
    assert len(errors) == 1
    assert "Duplicate provider ID: 'env'" in errors[0]

    # Create a spec with unique provider IDs
    spec = Spec(
        version="0.1",
        configuration_providers=[
            Provider(
                type="env",
                id="env",
                name="Test Environment",
                passthrough=True,
                filter_chain=[],
            ),
            Provider(
                type="dotenv",
                id="dotenv",  # Unique ID
                name="Dotenv Provider",
                passthrough=False,
                filter_chain=[],
            ),
        ],
        configuration_injectors=[],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    errors = validate_unique_provider_ids(spec)
    assert len(errors) == 0


def test_validate_unique_injector_names():
    """Test validation of unique injector names."""
    # Create a spec with duplicate injector names
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_var",
                kind="env_var",
                aliases=["TEST_VAR"],
                sources=["test_value"],
            ),
            Injector(
                name="test_var",  # Duplicate name
                kind="named",
                aliases=["--test"],
                sources=["test_value"],
            ),
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    errors = validate_unique_injector_names(spec)
    assert len(errors) == 1
    assert "Duplicate injector name: 'test_var'" in errors[0]

    # Create a spec with unique injector names
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_var",
                kind="env_var",
                aliases=["TEST_VAR"],
                sources=["test_value"],
            ),
            Injector(
                name="test_arg",  # Unique name
                kind="named",
                aliases=["--test"],
                sources=["test_value"],
            ),
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    errors = validate_unique_injector_names(spec)
    assert len(errors) == 0


def test_validate_alias_syntax():
    """Test validation of alias syntax."""
    # Create a spec with invalid env_var aliases
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_var",
                kind="env_var",
                aliases=["invalid-alias"],  # Invalid: contains hyphen
                sources=["test_value"],
            ),
            Injector(
                name="test_var2",
                kind="env_var",
                aliases=["1INVALID"],  # Invalid: starts with number
                sources=["test_value"],
            ),
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    errors = validate_alias_syntax(spec)
    assert len(errors) == 2
    assert "Invalid env_var alias 'invalid-alias'" in errors[0]
    assert "Invalid env_var alias '1INVALID'" in errors[1]

    # Create a spec with invalid named aliases
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_arg",
                kind="named",
                aliases=["test"],  # Invalid: doesn't start with -
                sources=["test_value"],
            ),
            Injector(
                name="test_arg2",
                kind="named",
                aliases=["--t"],  # Invalid: too short for long form
                sources=["test_value"],
            ),
            Injector(
                name="test_arg3",
                kind="named",
                aliases=["-too-long"],  # Invalid: too long for short form
                sources=["test_value"],
            ),
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    errors = validate_alias_syntax(spec)
    assert len(errors) == 3
    assert "Invalid named alias 'test'" in errors[0]
    assert "Invalid named alias '--t'" in errors[1]
    assert "Invalid named alias '-too-long'" in errors[2]

    # Create a spec with valid aliases
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_var",
                kind="env_var",
                aliases=["TEST_VAR"],  # Valid env_var alias
                sources=["test_value"],
            ),
            Injector(
                name="test_arg",
                kind="named",
                aliases=["--test", "-t"],  # Valid named aliases
                sources=["test_value"],
            ),
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    errors = validate_alias_syntax(spec)
    assert len(errors) == 0


def test_validate_positional_ordering():
    """Test validation of positional ordering."""
    # Create a spec with positional injectors missing order
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="pos1",
                kind="positional",
                aliases=[],
                sources=["value1"],
                order=None,  # Missing order
            )
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    errors = validate_positional_ordering(spec)
    assert len(errors) == 1
    assert "Positional injector 'pos1' must have an order value" in errors[0]

    # Create a spec with duplicate order values
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="pos1", kind="positional", aliases=[], sources=["value1"], order=1
            ),
            Injector(
                name="pos2",
                kind="positional",
                aliases=[],
                sources=["value2"],
                order=1,  # Duplicate order
            ),
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    errors = validate_positional_ordering(spec)
    assert len(errors) == 1
    assert "Positional injectors must have unique order values" in errors[0]

    # Create a spec with non-sequential order values
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="pos1", kind="positional", aliases=[], sources=["value1"], order=1
            ),
            Injector(
                name="pos2",
                kind="positional",
                aliases=[],
                sources=["value2"],
                order=3,  # Gap in sequence
            ),
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    errors = validate_positional_ordering(spec)
    assert len(errors) == 1
    assert "Positional injectors must have sequential order values" in errors[0]

    # Create a spec with valid positional ordering
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="pos1", kind="positional", aliases=[], sources=["value1"], order=1
            ),
            Injector(
                name="pos2", kind="positional", aliases=[], sources=["value2"], order=2
            ),
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    errors = validate_positional_ordering(spec)
    assert len(errors) == 0


def test_validate_strict_rules():
    """Test validation of strict rules."""
    # Create a spec with injectors missing aliases and sources
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_var",
                kind="env_var",
                aliases=[],  # Missing aliases
                sources=["test_value"],
            ),
            Injector(
                name="test_arg",
                kind="named",
                aliases=["--test"],
                sources=[],  # Missing sources
            ),
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    errors = validate_strict_rules(spec)
    assert len(errors) == 2
    assert "Injector 'test_var' should have at least one alias" in errors[0]
    assert "Injector 'test_arg' should have at least one source" in errors[1]

    # Create a spec that passes strict validation
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_var",
                kind="env_var",
                aliases=["TEST_VAR"],
                sources=["test_value"],
            ),
            Injector(
                name="test_arg",
                kind="named",
                aliases=["--test"],
                sources=["test_value"],
            ),
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    errors = validate_strict_rules(spec)
    assert len(errors) == 0


def test_semantic_validate():
    """Test the main semantic_validate function."""
    # Create a spec with multiple validation issues
    spec = Spec(
        version="0.1",
        configuration_providers=[
            Provider(
                type="env",
                id="env",
                name="Test Environment",
                passthrough=True,
                filter_chain=[],
            ),
            Provider(
                type="dotenv",
                id="env",  # Duplicate ID
                name="Dotenv Provider",
                passthrough=False,
                filter_chain=[],
            ),
        ],
        configuration_injectors=[
            Injector(
                name="test_var",
                kind="env_var",
                aliases=["invalid-alias"],  # Invalid alias
                sources=["test_value"],
            ),
            Injector(
                name="pos1",
                kind="positional",
                aliases=[],
                sources=["value1"],
                order=None,  # Missing order
            ),
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    # Test without strict mode
    errors = semantic_validate(spec, strict=False)
    assert (
        len(errors) == 3
    )  # 1 for duplicate ID, 1 for invalid alias, 1 for missing order

    # Test with strict mode
    errors = semantic_validate(spec, strict=True)
    assert len(errors) >= 4  # Additional errors from strict validation

    # Create a valid spec
    spec = Spec(
        version="0.1",
        configuration_providers=[
            Provider(
                type="env",
                id="env",
                name="Test Environment",
                passthrough=True,
                filter_chain=[],
            ),
            Provider(
                type="dotenv",
                id="dotenv",
                name="Dotenv Provider",
                passthrough=False,
                filter_chain=[],
            ),
        ],
        configuration_injectors=[
            Injector(
                name="test_var",
                kind="env_var",
                aliases=["TEST_VAR"],
                sources=["test_value"],
            ),
            Injector(
                name="test_arg",
                kind="named",
                aliases=["--test", "-t"],
                sources=["test_value"],
            ),
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    errors = semantic_validate(spec, strict=False)
    assert len(errors) == 0

    errors = semantic_validate(spec, strict=True)
    assert len(errors) == 0


if __name__ == "__main__":
    pytest.main([__file__])
