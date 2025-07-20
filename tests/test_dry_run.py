"""Tests for the dry-run functionality."""

import pytest

from config_injector.core import build_runtime_context, dry_run
from config_injector.models import Injector, Provider, Spec, Target


def test_dry_run_text_summary():
    """Test that dry-run generates a text summary."""
    # Create a test spec
    spec = Spec(
        version="0.1",
        configuration_providers=[
            Provider(
                type="env",
                id="env",
                name="Test Environment",
                passthrough=True,
                filter_chain=[],
            )
        ],
        configuration_injectors=[
            Injector(
                name="test_var",
                kind="env_var",
                aliases=["TEST_VAR"],
                sources=["test_value"],
            )
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    # Build runtime context
    context = build_runtime_context()

    # Perform dry run
    report = dry_run(spec, context)

    # Verify text summary
    assert isinstance(report.text_summary, str)
    assert "Providers Loaded" in report.text_summary
    assert "Injection Plan" in report.text_summary
    assert "Final Invocation" in report.text_summary


def test_dry_run_json_summary():
    """Test that dry-run generates a JSON summary."""
    # Create a test spec
    spec = Spec(
        version="0.1",
        configuration_providers=[
            Provider(
                type="env",
                id="env",
                name="Test Environment",
                passthrough=True,
                filter_chain=[],
            )
        ],
        configuration_injectors=[
            Injector(
                name="test_var",
                kind="env_var",
                aliases=["TEST_VAR"],
                sources=["test_value"],
            )
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    # Build runtime context
    context = build_runtime_context()

    # Perform dry run
    report = dry_run(spec, context)

    # Verify JSON summary
    assert isinstance(report.json_summary, dict)

    # Check structure of JSON summary
    assert "spec" in report.json_summary
    assert "providers" in report.json_summary
    assert "injections" in report.json_summary
    assert "build" in report.json_summary

    # Check spec section
    assert report.json_summary["spec"]["version"] == "0.1"
    assert report.json_summary["spec"]["working_dir"] == "/tmp"
    assert report.json_summary["spec"]["command"] == ["echo", "test"]

    # Check providers section
    assert "env" in report.json_summary["providers"]

    # Check injections section
    assert len(report.json_summary["injections"]) == 1
    assert report.json_summary["injections"][0]["name"] == "test_var"
    assert report.json_summary["injections"][0]["kind"] == "env_var"

    # Check build section
    assert "env_keys" in report.json_summary["build"]
    assert "argv" in report.json_summary["build"]
    assert report.json_summary["build"]["argv"] == ["echo", "test"]


def test_dry_run_sensitive_values():
    """Test that sensitive values are masked in the JSON summary."""
    # Create a test spec with sensitive injector
    spec = Spec(
        version="0.1",
        configuration_providers=[
            Provider(
                type="env",
                id="env",
                name="Test Environment",
                passthrough=True,
                filter_chain=[],
            )
        ],
        configuration_injectors=[
            Injector(
                name="password",
                kind="env_var",
                aliases=["PASSWORD"],
                sources=["secret123"],
                sensitive=True,
            )
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    # Build runtime context
    context = build_runtime_context()

    # Perform dry run
    report = dry_run(spec, context)

    # Verify sensitive values are masked in JSON summary
    assert report.json_summary["injections"][0]["sensitive"] is True
    assert report.json_summary["injections"][0]["value"] != "secret123"
    assert "<masked>" in report.json_summary["injections"][0]["value"]


if __name__ == "__main__":
    pytest.main([__file__])
