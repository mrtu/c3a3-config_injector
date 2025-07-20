"""Tests for the env_passthrough overlay logic."""

import os

import pytest

from config_injector.core import build_runtime_context, dry_run
from config_injector.models import Injector, Spec, Target


def test_env_passthrough_overlay():
    """Test that injector values win over passthrough values."""
    # Create a custom environment with a variable that will be overridden
    custom_env = os.environ.copy()
    custom_env["TEST_VAR"] = "passthrough_value"

    # Create a spec with env_passthrough=True and an injector that sets TEST_VAR
    spec = Spec(
        version="0.1",
        env_passthrough=True,
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_env_var",
                kind="env_var",
                aliases=["TEST_VAR"],
                sources=["injector_value"]
            )
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"])
    )

    # Build runtime context with the custom environment
    context = build_runtime_context(env=custom_env)

    # Perform dry run to get build result
    dry_run_result = dry_run(spec, context)

    # Verify that the injector value wins over the passthrough value
    assert dry_run_result.build.env["TEST_VAR"] == "injector_value"


def test_env_passthrough_disabled():
    """Test that when env_passthrough is disabled, only injector values are in the environment."""
    # Create a custom environment with a variable that won't be passed through
    custom_env = os.environ.copy()
    custom_env["TEST_VAR"] = "passthrough_value"
    custom_env["OTHER_VAR"] = "other_value"

    # Create a spec with env_passthrough=False and an injector that sets TEST_VAR
    spec = Spec(
        version="0.1",
        env_passthrough=False,
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_env_var",
                kind="env_var",
                aliases=["TEST_VAR"],
                sources=["injector_value"]
            )
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"])
    )

    # Build runtime context with the custom environment
    context = build_runtime_context(env=custom_env)

    # Perform dry run to get build result
    dry_run_result = dry_run(spec, context)

    # Verify that only the injector value is in the environment
    assert dry_run_result.build.env["TEST_VAR"] == "injector_value"
    assert "OTHER_VAR" not in dry_run_result.build.env


if __name__ == "__main__":
    pytest.main([__file__])
