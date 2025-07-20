"""Configuration providers for loading values from various sources."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .core import RuntimeContext
    from .models import FilterRule, Provider
    from .types import EnvMap, ProviderMap, ProviderMaps



# Try to import bitwarden_sdk classes at the module level
# These will be None if bitwarden_sdk is not installed
try:
    from bitwarden_sdk import BitwardenClient, ClientSettings
except ImportError:
    BitwardenClient = None
    ClientSettings = None


class ProviderProtocol(Protocol):
    """Protocol for configuration providers."""

    id: str

    def load(self, context: RuntimeContext) -> ProviderMap:
        """Load configuration values."""
        ...


class EnvProvider:
    """Environment variable provider."""

    def __init__(self, provider: Provider):
        self.id = provider.id
        self.provider = provider

    def load(self, context: RuntimeContext) -> ProviderMap:
        """Load environment variables."""
        env_map = context.env.copy()

        # Apply filters
        if self.provider.filter_chain:
            env_map = self._apply_filters(env_map, self.provider.filter_chain)

        return env_map

    def _apply_filters(self, env_map: EnvMap, filter_chain: list[FilterRule]) -> EnvMap:
        """Apply filter chain to environment map."""
        # Start with empty set and accumulate
        included_keys = set()

        for rule in filter_chain:
            if rule.include:
                pattern = re.compile(rule.include)
                for key in env_map:
                    if pattern.match(key):
                        included_keys.add(key)

            if rule.exclude:
                pattern = re.compile(rule.exclude)
                for key in list(included_keys):
                    if pattern.match(key):
                        included_keys.discard(key)

        return {k: v for k, v in env_map.items() if k in included_keys}


class DotenvProvider:
    """Dotenv file provider."""

    def __init__(self, provider: Provider):
        self.id = provider.id
        self.provider = provider

    def load(self, context: RuntimeContext) -> ProviderMap:
        """Load dotenv file."""
        if self.provider.hierarchical:
            return self._load_hierarchical(context)
        else:
            return self._load_single(context)

    def _load_single(self, context: RuntimeContext) -> ProviderMap:
        """Load a single dotenv file."""
        from dotenv import dotenv_values

        if self.provider.path:
            env_file = Path(self.provider.path)
        elif self.provider.filename:
            # Relative to working directory
            working_dir = Path(context.extra.get("working_dir", "."))
            env_file = working_dir / self.provider.filename
        else:
            return {}

        if not env_file.exists():
            return {}

        try:
            env_values = dotenv_values(env_file)
            env_map = {k: str(v) for k, v in env_values.items() if v is not None}

            # Apply filters
            if self.provider.filter_chain:
                env_map = self._apply_filters(env_map, self.provider.filter_chain)

            return env_map
        except Exception:
            return {}

    def _load_hierarchical(self, context: RuntimeContext) -> ProviderMap:
        """Load hierarchical dotenv files by walking up from working_dir to root and merging."""
        if not self.provider.filename:
            return {}

        # Determine the working directory: prefer context.extra, fallback to spec.target.working_dir, else cwd
        working_dir = Path(context.extra.get("working_dir") or getattr(context, "working_dir", None) or os.getcwd())
        env_files = []

        # Walk up directories from working_dir to root, collecting all matching dotenv files
        current_dir = working_dir.resolve()
        root_dir = current_dir.anchor
        while True:
            env_file = current_dir / self.provider.filename
            if env_file.exists():
                env_files.append(env_file)
            if str(current_dir) == root_dir:
                break
            current_dir = current_dir.parent

        # Merge files according to precedence (deep-first: closest to working_dir wins)
        return self._merge_hierarchical_dotenv(env_files, self.provider.precedence or "deep-first")

    def _merge_hierarchical_dotenv(self, files: list[Path], precedence: str) -> ProviderMap:
        """Merge hierarchical dotenv files according to precedence.
        For deep-first: closest (leaf) wins, so merge from root to leaf.
        For shallow-first: root wins, so merge from leaf to root.
        """
        from dotenv import dotenv_values

        merged = {}

        # Merge from root to leaf (so leaf/closest overrides) if deep-first, otherwise from leaf to root (so root/parent overrides)
        file_order = list(reversed(files)) if precedence == "deep-first" else files

        for env_file in file_order:
            try:
                env_values = dotenv_values(env_file)
                for k, v in env_values.items():
                    if v is not None:
                        merged[k] = str(v)
            except Exception:
                continue

        # Apply filters
        if self.provider.filter_chain:
            merged = self._apply_filters(merged, self.provider.filter_chain)

        return merged

    def _apply_filters(self, env_map: EnvMap, filter_chain: list[FilterRule]) -> EnvMap:
        """Apply filter chain to environment map."""
        # Start with empty set and accumulate
        included_keys = set()

        for rule in filter_chain:
            if rule.include:
                pattern = re.compile(rule.include)
                for key in env_map:
                    if pattern.match(key):
                        included_keys.add(key)

            if rule.exclude:
                pattern = re.compile(rule.exclude)
                for key in list(included_keys):
                    if pattern.match(key):
                        included_keys.discard(key)

        return {k: v for k, v in env_map.items() if k in included_keys}


class BwsProvider:
    """Bitwarden Secrets provider using official bitwarden-sdk."""

    def __init__(self, provider: Provider):
        self.id = provider.id
        self.provider = provider

    def load(self, context: RuntimeContext) -> ProviderMap:
        """Load secrets from Bitwarden Secrets Manager using official SDK."""
        from .token_engine import TokenEngine

        # Initialize token engine for expanding configuration values
        token_engine = TokenEngine(context)

        # Get configuration from provider
        vault_url = getattr(self.provider, "vault_url", None)
        access_token = getattr(self.provider, "access_token", None)

        if not vault_url or not access_token:
            # Fallback to environment variables if not configured
            vault_url = vault_url or context.env.get("BWS_VAULT_URL", "https://api.bitwarden.com")
            access_token = access_token or context.env.get("BWS_ACCESS_TOKEN")

        # Expand tokens in configuration values
        if vault_url:
            vault_url = token_engine.expand(vault_url)
        if access_token:
            access_token = token_engine.expand(access_token)

        # If no access token is configured, fall back to stub behavior for backward compatibility
        if not access_token:
            return self._load_stub_implementation(context)

        # Try to use the official bitwarden-sdk
        try:
            return self._load_with_sdk(vault_url, access_token, context)
        except ImportError:
            print("Warning: bitwarden-sdk not available, falling back to stub implementation")
            print("To use real Bitwarden integration, install: pip install bitwarden-sdk")
            return self._load_stub_implementation(context)
        except Exception as e:
            print(f"Warning: Failed to load secrets with SDK: {e}")
            return self._load_stub_implementation(context)

    def _load_stub_implementation(self, context: RuntimeContext) -> ProviderMap:
        """Fallback stub implementation for backward compatibility."""
        # Look for environment variables that might contain secret IDs
        raw_secrets = {}
        for key, value in context.env.items():
            if key.startswith("BWS_") or "SECRET" in key.upper():
                raw_secrets[key] = value

        # Apply filters to original keys first
        if self.provider.filter_chain:
            raw_secrets = self._apply_filters(raw_secrets, self.provider.filter_chain)

        # Convert keys to secret ID format after filtering
        secrets = {}
        for key, value in raw_secrets.items():
            secret_id = key.lower().replace("_", "-")
            secrets[secret_id] = value

        return secrets

    def _load_with_sdk(self, vault_url: str, access_token: str, context: RuntimeContext) -> ProviderMap:
        """Load secrets using the official bitwarden-sdk."""
        try:
            # Check if bitwarden_sdk is available (imported at module level)
            if BitwardenClient is None or ClientSettings is None:
                raise ImportError("bitwarden-sdk not available")

            # Create client settings
            settings = ClientSettings(
                api_url=vault_url,
                identity_url=vault_url.replace("api.", "identity."),
                device_type="SDK",
                user_agent="Configuration Wrapping Framework"
            )

            # Create and authenticate client
            client = BitwardenClient(settings)
            auth_result = client.auth().login_access_token(access_token)

            if not auth_result.get("success", False):
                raise Exception("Failed to authenticate with Bitwarden")

            # Extract secret IDs from context
            secret_ids = self._extract_secret_ids_from_context(context)

            # Fetch secrets using the SDK
            secrets = {}
            secrets_client = client.secrets()

            for secret_id in secret_ids:
                try:
                    secret_response = secrets_client.get(secret_id)
                    secrets[secret_id] = secret_response.value
                except Exception as e:
                    print(f"Warning: Failed to fetch secret {secret_id}: {e}")
                    continue

            # Apply filters if configured
            if self.provider.filter_chain:
                secrets = self._apply_filters(secrets, self.provider.filter_chain)

            return secrets

        except ImportError:
            raise ImportError("bitwarden-sdk not available") from None
        except Exception as e:
            raise Exception(f"SDK error: {e}") from e

    def _extract_secret_ids_from_context(self, context: RuntimeContext) -> list[str]:
        """Extract secret IDs from the runtime context."""
        # This is a simplified implementation
        # In a real implementation, we would parse the spec to find all PROVIDER:bws references
        secret_ids = []

        # Look for UUID patterns in environment variables as a fallback
        import re
        uuid_pattern = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

        for key, value in context.env.items():
            if "BWS_SECRET" in key.upper() or "BITWARDEN" in key.upper():
                matches = uuid_pattern.findall(value)
                secret_ids.extend(matches)

        return list(set(secret_ids))  # Remove duplicates

    def _apply_filters(self, env_map: EnvMap, filter_chain: list[FilterRule]) -> EnvMap:
        """Apply filter chain to environment map."""
        # Start with empty set and accumulate
        included_keys = set()

        for rule in filter_chain:
            if rule.include:
                pattern = re.compile(rule.include)
                for key in env_map:
                    if pattern.match(key):
                        included_keys.add(key)

            if rule.exclude:
                pattern = re.compile(rule.exclude)
                for key in list(included_keys):
                    if pattern.match(key):
                        included_keys.discard(key)

        return {k: v for k, v in env_map.items() if k in included_keys}


def create_provider(provider: Provider) -> ProviderProtocol:
    """Create a provider instance based on type."""
    if provider.type == "env":
        return EnvProvider(provider)
    elif provider.type == "dotenv":
        return DotenvProvider(provider)
    elif provider.type == "bws":
        return BwsProvider(provider)
    else:
        raise ValueError(f"Unknown provider type: {provider.type}")


def load_providers(spec, context: RuntimeContext) -> ProviderMaps:
    """Load all enabled providers."""
    providers = {}

    for provider_config in spec.configuration_providers:
        if not provider_config.enabled:
            continue

        provider = create_provider(provider_config)
        provider_map = provider.load(context)

        # Apply masking if configured
        if provider_config.mask:
            provider_map = dict.fromkeys(provider_map.keys(), "<masked>")

        providers[provider.id] = provider_map

    return providers
