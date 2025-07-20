"""Tests for the Bitwarden Secrets (BWS) provider."""

import os
from pathlib import Path

import pytest

from config_injector.models import Spec, Provider, Target
from config_injector.core import build_runtime_context
from config_injector.providers import BwsProvider, create_provider


def test_bws_provider_creation():
    """Test creating a BWS provider."""
    provider_config = Provider(
        type="bws",
        id="bws",
        name="Bitwarden Secrets",
        enabled=True
    )

    provider = create_provider(provider_config)

    assert isinstance(provider, BwsProvider)
    assert provider.id == "bws"


def test_bws_provider_loading():
    """Test loading secrets from the BWS provider stub."""
    # Clean up any existing BWS environment variables
    for key in list(os.environ.keys()):
        if key.startswith('BWS_') or 'SECRET' in key.upper() or 'BITWARDEN' in key.upper():
            del os.environ[key]

    # Create a spec with a BWS provider
    spec = Spec(
        version="0.1",
        configuration_providers=[
            Provider(
                type="bws",
                id="bws",
                name="Bitwarden Secrets",
                enabled=True
            )
        ],
        configuration_injectors=[],
        target=Target(working_dir="/tmp", command=["echo", "test"])
    )

    # Create a runtime context with environment variables that should be detected by the BWS provider
    os.environ["BWS_API_KEY"] = "test-api-key"
    os.environ["DATABASE_SECRET"] = "test-db-secret"

    context = build_runtime_context(spec)

    # Create and load the BWS provider
    provider_config = spec.configuration_providers[0]
    provider = BwsProvider(provider_config)
    provider_map = provider.load(context)

    # Verify that the BWS provider detected the environment variables
    assert "bws-api-key" in provider_map
    assert provider_map["bws-api-key"] == "test-api-key"
    assert "database-secret" in provider_map
    assert provider_map["database-secret"] == "test-db-secret"

    # Clean up environment variables after test
    for key in list(os.environ.keys()):
        if key.startswith('BWS_') or 'SECRET' in key.upper() or 'BITWARDEN' in key.upper():
            del os.environ[key]


def test_bws_provider_with_filter_chain():
    """Test BWS provider with filter chain."""
    # Clean up any existing BWS environment variables
    for key in list(os.environ.keys()):
        if key.startswith('BWS_') or 'SECRET' in key.upper() or 'BITWARDEN' in key.upper():
            del os.environ[key]

    # Create a spec with a BWS provider that has a filter chain
    spec = Spec(
        version="0.1",
        configuration_providers=[
            Provider(
                type="bws",
                id="bws",
                name="Bitwarden Secrets",
                enabled=True,
                filter_chain=[
                    {"include": "^BWS_.*$"}  # Only include keys starting with BWS_
                ]
            )
        ],
        configuration_injectors=[],
        target=Target(working_dir="/tmp", command=["echo", "test"])
    )

    # Create a runtime context with environment variables
    os.environ["BWS_API_KEY"] = "test-api-key"
    os.environ["DATABASE_SECRET"] = "test-db-secret"

    context = build_runtime_context(spec)

    # Create and load the BWS provider
    provider_config = spec.configuration_providers[0]
    provider = BwsProvider(provider_config)
    provider_map = provider.load(context)

    # Verify that only the BWS_ variable was included
    assert "bws-api-key" in provider_map
    assert provider_map["bws-api-key"] == "test-api-key"
    assert "database-secret" not in provider_map

    # Clean up environment variables after test
    for key in list(os.environ.keys()):
        if key.startswith('BWS_') or 'SECRET' in key.upper() or 'BITWARDEN' in key.upper():
            del os.environ[key]


def test_bws_provider_in_load_providers():
    """Test BWS provider in load_providers function."""
    from config_injector.providers import load_providers

    # Clean up any existing BWS environment variables
    for key in list(os.environ.keys()):
        if key.startswith('BWS_') or 'SECRET' in key.upper() or 'BITWARDEN' in key.upper():
            del os.environ[key]

    # Create a spec with a BWS provider
    spec = Spec(
        version="0.1",
        configuration_providers=[
            Provider(
                type="bws",
                id="bws",
                name="Bitwarden Secrets",
                enabled=True
            )
        ],
        configuration_injectors=[],
        target=Target(working_dir="/tmp", command=["echo", "test"])
    )

    # Create a runtime context with environment variables
    os.environ["BWS_API_KEY"] = "test-api-key"

    context = build_runtime_context(spec)
    providers = load_providers(spec, context)

    # Verify that the BWS provider was loaded
    assert "bws" in providers
    assert "bws-api-key" in providers["bws"]
    assert providers["bws"]["bws-api-key"] == "test-api-key"

    # Clean up environment variables after test
    for key in list(os.environ.keys()):
        if key.startswith('BWS_') or 'SECRET' in key.upper() or 'BITWARDEN' in key.upper():
            del os.environ[key]


if __name__ == "__main__":
    pytest.main([__file__])
