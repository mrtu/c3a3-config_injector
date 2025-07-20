"""Tests for CLI flags functionality."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from config_injector.cli import app


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def sample_spec_file():
    """Create a temporary spec file for testing."""
    spec_content = """
version: "0.1"
env_passthrough: false
mask_defaults: false
configuration_providers:
  - type: env
    id: env
    name: Environment Variables
    passthrough: true
    filter_chain: []
configuration_injectors:
  - name: test_var
    kind: env_var
    aliases: ["TEST_VAR"]
    sources: ["test_value"]
  - name: sensitive_var
    kind: env_var
    aliases: ["SECRET_VAR"]
    sources: ["secret_value"]
    sensitive: true
target:
  working_dir: "/tmp"
  command: ["echo", "test"]
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(spec_content)
        f.flush()
        yield Path(f.name)

    # Cleanup
    os.unlink(f.name)


@pytest.fixture
def profile_spec_file():
    """Create a temporary spec file with profiles for testing."""
    spec_content = """
version: "0.1"
env_passthrough: false
mask_defaults: false
configuration_providers:
  - type: env
    id: env
    name: Environment Variables
    passthrough: true
    filter_chain: []
configuration_injectors:
  - name: test_var
    kind: env_var
    aliases: ["TEST_VAR"]
    sources: ["test_value"]
target:
  working_dir: "/tmp"
  command: ["echo", "test"]
profiles:
  dev:
    env_passthrough: true
    mask_defaults: false
  prod:
    env_passthrough: false
    mask_defaults: true
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(spec_content)
        f.flush()
        yield Path(f.name)

    # Cleanup
    os.unlink(f.name)


def test_run_verbose_flag(runner, sample_spec_file):
    """Test the --verbose flag in run command."""
    result = runner.invoke(
        app, ["run", str(sample_spec_file), "--dry-run", "--verbose"]
    )

    assert result.exit_code == 0
    # In verbose mode with dry-run, we should see the dry run report
    assert "Dry Run Report" in result.stdout


def test_run_quiet_flag(runner, sample_spec_file):
    """Test the --quiet flag in run command."""
    result = runner.invoke(app, ["run", str(sample_spec_file), "--dry-run", "--quiet"])

    assert result.exit_code == 0
    # In quiet mode, there should be minimal output
    assert "Dry Run Report" not in result.stdout


def test_run_verbose_and_quiet_conflict(runner, sample_spec_file):
    """Test that --verbose and --quiet cannot be used together."""
    result = runner.invoke(app, ["run", str(sample_spec_file), "--verbose", "--quiet"])

    assert result.exit_code == 1
    assert "cannot be used together" in result.stdout


def test_run_profile_flag(runner, profile_spec_file):
    """Test the --profile flag in run command."""
    result = runner.invoke(
        app,
        ["run", str(profile_spec_file), "--dry-run", "--profile", "dev", "--verbose"],
    )

    assert result.exit_code == 0
    assert "Applying profile: dev" in result.stdout


def test_run_profile_not_found(runner, profile_spec_file):
    """Test --profile flag with non-existent profile."""
    result = runner.invoke(
        app, ["run", str(profile_spec_file), "--profile", "nonexistent"]
    )

    assert result.exit_code == 1
    assert "Profile 'nonexistent' not found" in result.stdout


def test_run_profile_no_profiles_defined(runner, sample_spec_file):
    """Test --profile flag when no profiles are defined."""
    result = runner.invoke(app, ["run", str(sample_spec_file), "--profile", "dev"])

    assert result.exit_code == 0  # Should warn but not fail
    assert "No profiles defined" in result.stdout


def test_run_env_passthrough_override(runner, sample_spec_file):
    """Test the --env-passthrough flag."""
    result = runner.invoke(
        app, ["run", str(sample_spec_file), "--dry-run", "--env-passthrough"]
    )

    assert result.exit_code == 0
    # The flag should override the spec setting


def test_run_no_env_passthrough_override(runner, sample_spec_file):
    """Test the --no-env-passthrough flag."""
    result = runner.invoke(
        app, ["run", str(sample_spec_file), "--dry-run", "--no-env-passthrough"]
    )

    assert result.exit_code == 0
    # The flag should override the spec setting


def test_run_mask_defaults_override(runner, sample_spec_file):
    """Test the --mask-defaults flag."""
    result = runner.invoke(
        app, ["run", str(sample_spec_file), "--dry-run", "--mask-defaults"]
    )

    assert result.exit_code == 0
    # The flag should override the spec setting


def test_run_no_mask_defaults_override(runner, sample_spec_file):
    """Test the --no-mask-defaults flag."""
    result = runner.invoke(
        app, ["run", str(sample_spec_file), "--dry-run", "--no-mask-defaults"]
    )

    assert result.exit_code == 0
    # The flag should override the spec setting


def test_run_strict_validation(runner, sample_spec_file):
    """Test the --strict flag in run command."""
    result = runner.invoke(app, ["run", str(sample_spec_file), "--dry-run", "--strict"])

    assert result.exit_code == 0
    # Should perform strict validation


def test_validate_verbose_flag(runner, sample_spec_file):
    """Test the --verbose flag in validate command."""
    result = runner.invoke(app, ["validate", str(sample_spec_file), "--verbose"])

    assert result.exit_code == 0
    assert "Loaded specification from" in result.stdout
    assert "Performing dry run validation" in result.stdout
    assert "Performing semantic validation" in result.stdout


def test_validate_quiet_flag(runner, sample_spec_file):
    """Test the --quiet flag in validate command."""
    result = runner.invoke(app, ["validate", str(sample_spec_file), "--quiet"])

    assert result.exit_code == 0
    # In quiet mode, success message should not be shown
    assert "Specification is valid" not in result.stdout


def test_validate_strict_flag(runner, sample_spec_file):
    """Test the --strict flag in validate command."""
    result = runner.invoke(app, ["validate", str(sample_spec_file), "--strict"])

    assert result.exit_code == 0
    assert "Specification is valid (strict mode)" in result.stdout


def test_validate_verbose_and_quiet_conflict(runner, sample_spec_file):
    """Test that --verbose and --quiet cannot be used together in validate."""
    result = runner.invoke(
        app, ["validate", str(sample_spec_file), "--verbose", "--quiet"]
    )

    assert result.exit_code == 1
    assert "cannot be used together" in result.stdout


def test_explain_verbose_flag(runner, sample_spec_file):
    """Test the --verbose flag in explain command."""
    result = runner.invoke(app, ["explain", str(sample_spec_file), "--verbose"])

    assert result.exit_code == 0
    assert "Loaded specification from" in result.stdout


def test_explain_quiet_flag(runner, sample_spec_file):
    """Test the --quiet flag in explain command."""
    result = runner.invoke(app, ["explain", str(sample_spec_file), "--quiet"])

    assert result.exit_code == 0
    # Should still show tables but with minimal extra output


def test_explain_verbose_and_quiet_conflict(runner, sample_spec_file):
    """Test that --verbose and --quiet cannot be used together in explain."""
    result = runner.invoke(
        app, ["explain", str(sample_spec_file), "--verbose", "--quiet"]
    )

    assert result.exit_code == 1
    assert "cannot be used together" in result.stdout


def test_json_output_flag(runner, sample_spec_file):
    """Test the --json flag with dry-run."""
    result = runner.invoke(app, ["run", str(sample_spec_file), "--dry-run", "--json"])

    assert result.exit_code == 0
    # Should output valid JSON
    import json

    try:
        json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail("Output is not valid JSON")


def test_json_output_without_dry_run(runner, sample_spec_file):
    """Test that --json flag shows warning without --dry-run."""
    result = runner.invoke(app, ["run", str(sample_spec_file), "--json"])

    # Should show warning but not fail
    assert "Warning: --json flag is ignored without --dry-run" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__])
