"""Tests for the Bitwarden Secrets (BWS) provider SDK implementation."""

import os
from unittest.mock import MagicMock, patch

import pytest

from config_injector.core import build_runtime_context
from config_injector.models import Provider, Spec, Target
from config_injector.providers import BwsProvider


def test_bws_sdk_provider_import_error():
    """Test BWS provider fallback when bitwarden-sdk import fails."""
    # Clean up any existing BWS environment variables
    for key in list(os.environ.keys()):
        if key.startswith("BWS_"):
            del os.environ[key]

    # Set environment variable before building context
    os.environ["BWS_API_KEY"] = "test-api-key"

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
                vault_url="https://api.bitwarden.com"
            )
        ],
        configuration_injectors=[],
        target=Target(working_dir="/tmp", command=["echo", "test"])
    )

    # Create a runtime context
    context = build_runtime_context()

    # Mock the BitwardenClient and ClientSettings to be None (as if import failed)
    with patch("config_injector.providers.BitwardenClient", None), \
         patch("config_injector.providers.ClientSettings", None):
        # Create and load the BWS provider
        provider_config = spec.configuration_providers[0]
        provider = BwsProvider(provider_config)
        provider_map = provider.load(context)

    # Verify that the provider fell back to the stub implementation
    # The stub implementation should look for environment variables with BWS_ prefix
    assert "bws-api-key" in provider_map
    assert provider_map["bws-api-key"] == "test-api-key"

    # Clean up environment variables after test
    for key in list(os.environ.keys()):
        if key.startswith("BWS_"):
            del os.environ[key]


def test_bws_sdk_provider_success():
    """Test BWS provider with SDK implementation."""
    # Clean up any existing BWS environment variables
    for key in list(os.environ.keys()):
        if key.startswith("BWS_"):
            del os.environ[key]

    # Create mock objects
    mock_client = MagicMock()
    mock_auth = MagicMock()
    mock_secrets_client = MagicMock()
    mock_bitwarden_client = MagicMock()
    mock_client_settings = MagicMock()

    # Configure the mocks
    mock_bitwarden_client.return_value = mock_client
    mock_client.auth.return_value = mock_auth
    mock_client.secrets.return_value = mock_secrets_client

    # Mock successful authentication
    mock_auth.login_access_token.return_value = {"success": True}

    # Mock secret response
    mock_secret = MagicMock()
    mock_secret.value = "secret-value"
    mock_secrets_client.get.return_value = mock_secret

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
                vault_url="https://api.bitwarden.com"
            )
        ],
        configuration_injectors=[],
        target=Target(working_dir="/tmp", command=["echo", "test"])
    )

    # Create a runtime context with environment variables containing secret IDs
    os.environ["BWS_SECRET_ID"] = "12345678-1234-1234-1234-123456789012"
    context = build_runtime_context()

    # Patch the module-level imports with our mocks
    with patch("config_injector.providers.BitwardenClient", mock_bitwarden_client), \
         patch("config_injector.providers.ClientSettings", mock_client_settings):
        # Create and load the BWS provider
        provider_config = spec.configuration_providers[0]
        provider = BwsProvider(provider_config)
        provider_map = provider.load(context)

        # Verify that the SDK implementation was used
        mock_bitwarden_client.assert_called_once()
        mock_auth.login_access_token.assert_called_once_with("test-access-token")
        mock_secrets_client.get.assert_called_once_with("12345678-1234-1234-1234-123456789012")

        # Verify that the secret was loaded
        assert "12345678-1234-1234-1234-123456789012" in provider_map
        assert provider_map["12345678-1234-1234-1234-123456789012"] == "secret-value"

    # Clean up environment variables after test
    for key in list(os.environ.keys()):
        if key.startswith("BWS_"):
            del os.environ[key]


def test_bws_sdk_provider_auth_failure():
    """Test BWS provider with SDK implementation when authentication fails."""
    # Clean up any existing BWS environment variables
    for key in list(os.environ.keys()):
        if key.startswith("BWS_"):
            del os.environ[key]

    # Create mock objects
    mock_client = MagicMock()
    mock_auth = MagicMock()
    mock_bitwarden_client = MagicMock()
    mock_client_settings = MagicMock()

    # Configure the mocks
    mock_bitwarden_client.return_value = mock_client
    mock_client.auth.return_value = mock_auth

    # Mock failed authentication
    mock_auth.login_access_token.return_value = {"success": False, "message": "Invalid token"}

    # Create a spec with a BWS provider
    spec = Spec(
        version="0.1",
        configuration_providers=[
            Provider(
                type="bws",
                id="bws",
                name="Bitwarden Secrets",
                enabled=True,
                access_token="invalid-token",
                vault_url="https://api.bitwarden.com"
            )
        ],
        configuration_injectors=[],
        target=Target(working_dir="/tmp", command=["echo", "test"])
    )

    # Set environment variable before building context for stub fallback
    os.environ["BWS_API_KEY"] = "test-api-key"

    # Create a runtime context
    context = build_runtime_context()

    # Patch the module-level imports with our mocks
    with patch("config_injector.providers.BitwardenClient", mock_bitwarden_client), \
         patch("config_injector.providers.ClientSettings", mock_client_settings):
        # Create and load the BWS provider
        provider_config = spec.configuration_providers[0]
        provider = BwsProvider(provider_config)

        # The provider should fall back to the stub implementation when authentication fails
        provider_map = provider.load(context)

        # Verify that authentication was attempted
        mock_bitwarden_client.assert_called_once()
        mock_auth.login_access_token.assert_called_once_with("invalid-token")

        # Verify that the provider fell back to the stub implementation
        assert "bws-api-key" in provider_map
        assert provider_map["bws-api-key"] == "test-api-key"

    # Clean up environment variables after test
    for key in list(os.environ.keys()):
        if key.startswith("BWS_"):
            del os.environ[key]


def test_bws_sdk_provider_secret_fetch_error():
    """Test BWS provider with SDK implementation when fetching a secret fails."""
    # Clean up any existing BWS environment variables
    for key in list(os.environ.keys()):
        if key.startswith("BWS_"):
            del os.environ[key]

    # Create mock objects
    mock_client = MagicMock()
    mock_auth = MagicMock()
    mock_secrets_client = MagicMock()
    mock_bitwarden_client = MagicMock()
    mock_client_settings = MagicMock()

    # Configure the mocks
    mock_bitwarden_client.return_value = mock_client
    mock_client.auth.return_value = mock_auth
    mock_client.secrets.return_value = mock_secrets_client

    # Mock successful authentication
    mock_auth.login_access_token.return_value = {"success": True}

    # Mock secret fetch error
    mock_secrets_client.get.side_effect = Exception("Secret not found")

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
                vault_url="https://api.bitwarden.com"
            )
        ],
        configuration_injectors=[],
        target=Target(working_dir="/tmp", command=["echo", "test"])
    )

    # Create a runtime context with environment variables containing secret IDs
    os.environ["BWS_SECRET_ID"] = "12345678-1234-1234-1234-123456789012"
    context = build_runtime_context()

    # Patch the module-level imports with our mocks
    with patch("config_injector.providers.BitwardenClient", mock_bitwarden_client), \
         patch("config_injector.providers.ClientSettings", mock_client_settings):
        # Create and load the BWS provider
        provider_config = spec.configuration_providers[0]
        provider = BwsProvider(provider_config)
        provider_map = provider.load(context)

        # Verify that the SDK implementation was used
        mock_bitwarden_client.assert_called_once()
        mock_auth.login_access_token.assert_called_once_with("test-access-token")
        mock_secrets_client.get.assert_called_once_with("12345678-1234-1234-1234-123456789012")

        # Verify that the secret was not loaded (should be an empty map since the secret fetch failed)
        assert "12345678-1234-1234-1234-123456789012" not in provider_map
        assert len(provider_map) == 0

    # Clean up environment variables after test
    for key in list(os.environ.keys()):
        if key.startswith("BWS_"):
            del os.environ[key]


def test_bws_sdk_provider_with_filter_chain():
    """Test BWS provider with SDK implementation and filter chain."""
    # Clean up any existing BWS environment variables
    for key in list(os.environ.keys()):
        if key.startswith("BWS_"):
            del os.environ[key]

    # Create mock objects
    mock_client = MagicMock()
    mock_auth = MagicMock()
    mock_secrets_client = MagicMock()
    mock_bitwarden_client = MagicMock()
    mock_client_settings = MagicMock()

    # Configure the mocks
    mock_bitwarden_client.return_value = mock_client
    mock_client.auth.return_value = mock_auth
    mock_client.secrets.return_value = mock_secrets_client

    # Mock successful authentication
    mock_auth.login_access_token.return_value = {"success": True}

    # Mock secret responses
    mock_secret1 = MagicMock()
    mock_secret1.value = "secret-value-1"
    mock_secret2 = MagicMock()
    mock_secret2.value = "secret-value-2"

    # Configure get to return different values based on the secret ID
    def get_secret(secret_id):
        if secret_id == "12345678-1234-1234-1234-123456789012":
            return mock_secret1
        elif secret_id == "87654321-4321-4321-4321-210987654321":
            return mock_secret2
        raise Exception("Secret not found")

    mock_secrets_client.get.side_effect = get_secret

    # Create a spec with a BWS provider that has a filter chain
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
                filter_chain=[
                    {"include": "^1234.*$"}  # Only include keys starting with 1234
                ]
            )
        ],
        configuration_injectors=[],
        target=Target(working_dir="/tmp", command=["echo", "test"])
    )

    # Create a runtime context with environment variables containing secret IDs
    os.environ["BWS_SECRET_ID_1"] = "12345678-1234-1234-1234-123456789012"
    os.environ["BWS_SECRET_ID_2"] = "87654321-4321-4321-4321-210987654321"
    context = build_runtime_context()

    # Patch the module-level imports with our mocks
    with patch("config_injector.providers.BitwardenClient", mock_bitwarden_client), \
         patch("config_injector.providers.ClientSettings", mock_client_settings):
        # Create and load the BWS provider
        provider_config = spec.configuration_providers[0]
        provider = BwsProvider(provider_config)
        provider_map = provider.load(context)

        # Verify that the SDK implementation was used
        mock_bitwarden_client.assert_called_once()
        mock_auth.login_access_token.assert_called_once_with("test-access-token")

        # Verify that both secrets were fetched
        assert mock_secrets_client.get.call_count == 2

        # Verify that only the secret matching the filter was included
        assert "12345678-1234-1234-1234-123456789012" in provider_map
        assert provider_map["12345678-1234-1234-1234-123456789012"] == "secret-value-1"
        assert "87654321-4321-4321-4321-210987654321" not in provider_map

    # Clean up environment variables after test
    for key in list(os.environ.keys()):
        if key.startswith("BWS_"):
            del os.environ[key]


def test_bws_sdk_provider_token_expansion():
    """Test BWS provider with SDK implementation and token expansion."""
    # Clean up any existing BWS environment variables
    for key in list(os.environ.keys()):
        if key.startswith("BWS_"):
            del os.environ[key]

    # Create mock objects
    mock_client = MagicMock()
    mock_auth = MagicMock()
    mock_secrets_client = MagicMock()
    mock_bitwarden_client = MagicMock()

    # Create a mock ClientSettings that captures the arguments
    def mock_client_settings_factory(**kwargs):
        mock_settings = MagicMock()
        # Set the attributes based on the arguments passed
        for key, value in kwargs.items():
            setattr(mock_settings, key, value)
        return mock_settings

    mock_client_settings = MagicMock(side_effect=mock_client_settings_factory)

    # Configure the mocks
    mock_bitwarden_client.return_value = mock_client
    mock_client.auth.return_value = mock_auth
    mock_client.secrets.return_value = mock_secrets_client

    # Mock successful authentication
    mock_auth.login_access_token.return_value = {"success": True}

    # Mock secret response
    mock_secret = MagicMock()
    mock_secret.value = "secret-value"
    mock_secrets_client.get.return_value = mock_secret

    # Create a spec with a BWS provider using token expansion
    spec = Spec(
        version="0.1",
        configuration_providers=[
            Provider(
                type="bws",
                id="bws",
                name="Bitwarden Secrets",
                enabled=True,
                access_token="${ENV:BWS_TOKEN}",
                vault_url="${ENV:BWS_URL|https://api.bitwarden.com}"
            )
        ],
        configuration_injectors=[],
        target=Target(working_dir="/tmp", command=["echo", "test"])
    )

    # Set environment variables for token expansion
    os.environ["BWS_TOKEN"] = "expanded-token"
    os.environ["BWS_URL"] = "https://custom.bitwarden.com"

    # Create a runtime context with environment variables containing secret IDs
    os.environ["BWS_SECRET_ID"] = "12345678-1234-1234-1234-123456789012"
    context = build_runtime_context()

    # Patch the module-level imports with our mocks
    with patch("config_injector.providers.BitwardenClient", mock_bitwarden_client), \
         patch("config_injector.providers.ClientSettings", mock_client_settings):
        # Create and load the BWS provider
        provider_config = spec.configuration_providers[0]
        provider = BwsProvider(provider_config)
        provider_map = provider.load(context)

        # Verify that the SDK implementation was used with expanded tokens
        mock_bitwarden_client.assert_called_once()
        mock_auth.login_access_token.assert_called_once_with("expanded-token")

        # Verify that the client was created with the expanded URL
        settings_kwargs = mock_bitwarden_client.call_args[0][0]
        assert settings_kwargs.api_url == "https://custom.bitwarden.com"

        # Verify that the secret was loaded
        assert "12345678-1234-1234-1234-123456789012" in provider_map
        assert provider_map["12345678-1234-1234-1234-123456789012"] == "secret-value"

    # Clean up environment variables after test
    for key in list(os.environ.keys()):
        if key.startswith("BWS_"):
            del os.environ[key]


if __name__ == "__main__":
    pytest.main([__file__])
