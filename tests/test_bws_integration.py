"""Tests for the Bitwarden Secrets (BWS) provider integration.

This test file covers the integration of the Bitwarden Secrets provider with the framework,
focusing on both the stub implementation and the SDK implementation. The tests verify:

1. Creating a BWS provider
2. Fallback to stub implementation when no access token is provided
3. Applying filter chains to the loaded secrets
4. Integration with the load_providers function
5. Token expansion in the provider configuration
6. Fallback to stub implementation when the SDK raises an error
7. Extracting secret IDs from the runtime context

The tests are designed to work without requiring the actual bitwarden-sdk to be installed,
by mocking the relevant methods of the BwsProvider class rather than trying to mock the
import of the SDK itself.
"""

import os
from unittest.mock import patch

import pytest

from config_injector.core import build_runtime_context
from config_injector.models import Provider, Spec, Target
from config_injector.providers import BwsProvider, create_provider


def test_bws_provider_creation():
    """Test creating a BWS provider."""
    provider_config = Provider(
        type="bws", id="bws", name="Bitwarden Secrets", enabled=True
    )

    provider = create_provider(provider_config)

    assert isinstance(provider, BwsProvider)
    assert provider.id == "bws"


def test_bws_provider_stub_fallback():
    """Test BWS provider fallback to stub implementation when no access token is provided."""
    # Clean up any existing BWS environment variables
    for key in list(os.environ.keys()):
        if key.startswith("BWS_") or "SECRET" in key.upper():
            del os.environ[key]

    # Create a spec with a BWS provider without access token
    spec = Spec(
        version="0.1",
        configuration_providers=[
            Provider(type="bws", id="bws", name="Bitwarden Secrets", enabled=True)
        ],
        configuration_injectors=[],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    # Create a runtime context with environment variables
    os.environ["BWS_API_KEY"] = "test-api-key"
    os.environ["DATABASE_SECRET"] = "test-db-secret"

    context = build_runtime_context()

    # Create and load the BWS provider
    provider_config = spec.configuration_providers[0]
    provider = BwsProvider(provider_config)
    provider_map = provider.load(context)

    # Verify that the BWS provider used the stub implementation
    assert "bws-api-key" in provider_map
    assert provider_map["bws-api-key"] == "test-api-key"
    assert "database-secret" in provider_map
    assert provider_map["database-secret"] == "test-db-secret"

    # Clean up environment variables after test
    for key in list(os.environ.keys()):
        if key.startswith("BWS_") or "SECRET" in key.upper():
            del os.environ[key]


def test_bws_provider_with_filter_chain():
    """Test BWS provider with filter chain."""
    # Clean up any existing BWS environment variables
    for key in list(os.environ.keys()):
        if key.startswith("BWS_") or "SECRET" in key.upper():
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
                ],
            )
        ],
        configuration_injectors=[],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    # Create a runtime context with environment variables
    os.environ["BWS_API_KEY"] = "test-api-key"
    os.environ["DATABASE_SECRET"] = "test-db-secret"

    context = build_runtime_context()

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
        if key.startswith("BWS_") or "SECRET" in key.upper():
            del os.environ[key]


def test_bws_provider_in_load_providers():
    """Test BWS provider in load_providers function."""
    from config_injector.providers import load_providers

    # Clean up any existing BWS environment variables
    for key in list(os.environ.keys()):
        if key.startswith("BWS_") or "SECRET" in key.upper():
            del os.environ[key]

    # Create a spec with a BWS provider
    spec = Spec(
        version="0.1",
        configuration_providers=[
            Provider(type="bws", id="bws", name="Bitwarden Secrets", enabled=True)
        ],
        configuration_injectors=[],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    # Create a runtime context with environment variables
    os.environ["BWS_API_KEY"] = "test-api-key"

    context = build_runtime_context()
    providers = load_providers(spec, context)

    # Verify that the BWS provider was loaded
    assert "bws" in providers
    assert "bws-api-key" in providers["bws"]
    assert providers["bws"]["bws-api-key"] == "test-api-key"

    # Clean up environment variables after test
    for key in list(os.environ.keys()):
        if key.startswith("BWS_") or "SECRET" in key.upper():
            del os.environ[key]


# The following tests verify the behavior when the bitwarden-sdk is available
# but they don't actually try to import it, instead they mock the methods
# that would use it


def test_bws_provider_token_expansion():
    """Test token expansion in BWS provider configuration."""
    # Clean up any existing BWS environment variables
    for key in list(os.environ.keys()):
        if (
            key.startswith("BWS_")
            or "SECRET" in key.upper()
            or "BITWARDEN" in key.upper()
        ):
            del os.environ[key]

    # Create a spec with a BWS provider using token expansion
    spec = Spec(
        version="0.1",
        configuration_providers=[
            Provider(
                type="bws",
                id="bws",
                name="Bitwarden Secrets",
                enabled=True,
                access_token="${ENV:BWS_TOKEN|fallback-token}",
                vault_url="${ENV:BWS_URL|https://api.bitwarden.com}",
            )
        ],
        configuration_injectors=[],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    # Set environment variables for token expansion
    os.environ["BWS_TOKEN"] = "expanded-token"
    os.environ["BWS_URL"] = "https://custom.bitwarden.com"

    # Create a runtime context
    context = build_runtime_context()

    # Create the BWS provider
    provider_config = spec.configuration_providers[0]
    provider = BwsProvider(provider_config)

    # Mock the _load_with_sdk method to verify the expanded tokens
    with patch.object(
        provider, "_load_with_sdk", return_value={}
    ) as mock_load_with_sdk:
        provider.load(context)

        # Verify that _load_with_sdk was called with the expanded tokens
        mock_load_with_sdk.assert_called_once()
        args, _ = mock_load_with_sdk.call_args
        assert args[0] == "https://custom.bitwarden.com"  # vault_url
        assert args[1] == "expanded-token"  # access_token

    # Clean up environment variables after test
    for key in list(os.environ.keys()):
        if (
            key.startswith("BWS_")
            or "SECRET" in key.upper()
            or "BITWARDEN" in key.upper()
        ):
            del os.environ[key]


def test_bws_provider_fallback_on_sdk_error():
    """Test BWS provider fallback to stub implementation when SDK raises an error."""
    # Clean up any existing BWS environment variables
    for key in list(os.environ.keys()):
        if (
            key.startswith("BWS_")
            or "SECRET" in key.upper()
            or "BITWARDEN" in key.upper()
        ):
            del os.environ[key]

    # Create a spec with a BWS provider
    spec = Spec(
        version="0.1",
        configuration_providers=[
            Provider(
                type="bws",
                id="bws",
                name="Bitwarden Secrets",
                enabled=True,
                access_token="test-access-token",
                vault_url="https://api.bitwarden.com",
            )
        ],
        configuration_injectors=[],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    # Create a runtime context with environment variables
    os.environ["BWS_API_KEY"] = "test-api-key"

    context = build_runtime_context()

    # Create the BWS provider
    provider_config = spec.configuration_providers[0]
    provider = BwsProvider(provider_config)

    # Mock the BitwardenClient to raise an exception
    with patch("config_injector.providers.BitwardenClient") as mock_client:
        mock_client.side_effect = Exception("SDK error")

        # Load the provider
        provider_map = provider.load(context)

        # Verify that the provider fell back to the stub implementation
        assert "bws-api-key" in provider_map
        assert provider_map["bws-api-key"] == "test-api-key"

    # Clean up environment variables after test
    for key in list(os.environ.keys()):
        if (
            key.startswith("BWS_")
            or "SECRET" in key.upper()
            or "BITWARDEN" in key.upper()
        ):
            del os.environ[key]


def test_bws_provider_extract_secret_ids():
    """Test extracting secret IDs from the runtime context."""
    # Clean up any existing BWS environment variables
    for key in list(os.environ.keys()):
        if (
            key.startswith("BWS_")
            or "SECRET" in key.upper()
            or "BITWARDEN" in key.upper()
        ):
            del os.environ[key]

    # Create a spec with a BWS provider
    spec = Spec(
        version="0.1",
        configuration_providers=[
            Provider(
                type="bws",
                id="bws",
                name="Bitwarden Secrets",
                enabled=True,
                access_token="test-access-token",
                vault_url="https://api.bitwarden.com",
            )
        ],
        configuration_injectors=[],
        target=Target(working_dir="/tmp", command=["echo", "test"]),
    )

    # Create a runtime context with environment variables containing secret IDs
    os.environ["BWS_SECRET_ID"] = "12345678-1234-1234-1234-123456789012"
    os.environ["BITWARDEN_SECRET"] = "87654321-4321-4321-4321-210987654321"

    context = build_runtime_context()

    # Create the BWS provider
    provider_config = spec.configuration_providers[0]
    provider = BwsProvider(provider_config)

    # Call the _extract_secret_ids_from_context method
    secret_ids = provider._extract_secret_ids_from_context(context)

    # Verify that the secret IDs were extracted
    assert "12345678-1234-1234-1234-123456789012" in secret_ids
    assert "87654321-4321-4321-4321-210987654321" in secret_ids

    # Clean up environment variables after test
    for key in list(os.environ.keys()):
        if (
            key.startswith("BWS_")
            or "SECRET" in key.upper()
            or "BITWARDEN" in key.upper()
        ):
            del os.environ[key]


if __name__ == "__main__":
    pytest.main([__file__])
