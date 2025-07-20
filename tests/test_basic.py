"""Basic tests for the Configuration Wrapping Framework."""

import os
import tempfile
from pathlib import Path

import pytest

from config_injector.core import build_runtime_context, load_spec
from config_injector.models import Provider, Spec, Target


def test_load_spec():
    """Test loading a basic specification."""
    spec_data = {
        "version": "0.1",
        "env_passthrough": True,
        "configuration_providers": [
            {
                "type": "env",
                "id": "env",
                "name": "Host Environment",
                "passthrough": True,
                "filter_chain": [],
            }
        ],
        "configuration_injectors": [
            {
                "name": "test_var",
                "kind": "env_var",
                "aliases": ["TEST_VAR"],
                "sources": ["${ENV:TEST_SOURCE}"],
            }
        ],
        "target": {"working_dir": "/tmp", "command": ["echo", "test"]},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        import yaml

        yaml.dump(spec_data, f)
        spec_path = Path(f.name)

    try:
        spec = load_spec(spec_path)
        assert spec.version == "0.1"
        assert spec.env_passthrough is True
        assert len(spec.configuration_providers) == 1
        assert len(spec.configuration_injectors) == 1
        assert spec.configuration_providers[0].type == "env"
        assert spec.configuration_injectors[0].name == "test_var"
    finally:
        spec_path.unlink()


def test_build_runtime_context():
    """Test building runtime context."""
    context = build_runtime_context()

    assert context.pid == os.getpid()
    assert context.home == str(Path.home())
    assert "PATH" in context.env  # Should have environment variables


def test_token_expansion():
    """Test basic token expansion."""
    from config_injector.core import RuntimeContext
    from config_injector.token_engine import TokenEngine

    # Set up test environment
    test_env = {"TEST_VAR": "test_value", "HOME": "/test/home"}
    context = RuntimeContext(
        env=test_env,
        now=None,  # Will be set by build_runtime_context
        pid=12345,
        home="/test/home",
        seq=1,
    )

    token_engine = TokenEngine(context)

    # Test environment variable expansion
    result = token_engine.expand("${ENV:TEST_VAR}")
    assert result == "test_value"

    # Test HOME token
    result = token_engine.expand("${HOME}")
    assert result == "/test/home"

    # Test PID token
    result = token_engine.expand("${PID}")
    assert result == "12345"


def test_provider_loading():
    """Test provider loading."""
    from config_injector.providers import load_providers

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
        configuration_injectors=[],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    context = build_runtime_context()
    providers = load_providers(spec, context)

    assert "env" in providers
    assert len(providers["env"]) > 0  # Should have environment variables


if __name__ == "__main__":
    pytest.main([__file__])
