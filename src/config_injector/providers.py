"""Configuration providers for loading values from various sources."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from .models import FilterRule

if TYPE_CHECKING:
    from .core import RuntimeContext
    from .models import Provider
    from .types import EnvMap, ProviderMap, ProviderMaps

# Try to import bitwarden_sdk classes at the module level
# These will be None if bitwarden_sdk is not installed
try:
    from bitwarden_sdk import (  # type: ignore[import-not-found]
        BitwardenClient,
        ClientSettings,
    )
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

    def _apply_filters(
        self, env_map: EnvMap, filter_chain: list[FilterRule | dict[str, str] | str]
    ) -> EnvMap:
        """Apply filter chain to environment map."""
        # Start with empty set and accumulate
        included_keys = set()

        for rule in filter_chain:
            if isinstance(rule, FilterRule):
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
            elif isinstance(rule, dict):
                # Convert dict to FilterRule
                filter_rule = FilterRule(**rule)
                if filter_rule.include:
                    pattern = re.compile(filter_rule.include)
                    for key in env_map:
                        if pattern.match(key):
                            included_keys.add(key)

                if filter_rule.exclude:
                    pattern = re.compile(filter_rule.exclude)
                    for key in list(included_keys):
                        if pattern.match(key):
                            included_keys.discard(key)
            elif isinstance(rule, str):
                # Treat string as include pattern
                pattern = re.compile(rule)
                for key in env_map:
                    if pattern.match(key):
                        included_keys.add(key)

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

        # Load dotenv values and filter out None values
        raw_env_map = dict(dotenv_values(env_file))
        env_map = {k: str(v) for k, v in raw_env_map.items() if v is not None}

        # Apply filters
        if self.provider.filter_chain:
            env_map = self._apply_filters(env_map, self.provider.filter_chain)

        return env_map

    def _load_hierarchical(self, context: RuntimeContext) -> ProviderMap:
        """Load hierarchical dotenv files."""
        if not self.provider.filename:
            return {}

        # Find all matching files by walking up the directory tree
        working_dir = Path(context.extra.get("working_dir", "."))
        filename = self.provider.filename
        files = []

        # Walk up the directory tree from working_dir
        current_dir = working_dir.resolve()
        while current_dir.exists():
            env_file = current_dir / filename
            if env_file.exists():
                files.append(env_file)
            # Move up one level
            parent = current_dir.parent
            if parent == current_dir:  # Reached root directory
                break
            current_dir = parent

        if not files:
            return {}

        # Sort files by depth (shallowest first)
        files.sort(key=lambda f: len(f.parts))

        # Merge files based on precedence
        precedence = self.provider.precedence or "deep-first"
        return self._merge_hierarchical_dotenv(files, precedence)

    def _merge_hierarchical_dotenv(
        self, files: list[Path], precedence: str
    ) -> ProviderMap:
        """Merge hierarchical dotenv files."""
        from dotenv import dotenv_values

        merged = {}

        if precedence == "deep-first":
            # Deepest files override shallowest
            for file_path in files:
                raw_file_env = dict(dotenv_values(file_path))
                file_env = {k: str(v) for k, v in raw_file_env.items() if v is not None}
                merged.update(file_env)
        else:
            # Shallowest files override deepest (default)
            for file_path in reversed(files):
                raw_file_env = dict(dotenv_values(file_path))
                file_env = {k: str(v) for k, v in raw_file_env.items() if v is not None}
                merged.update(file_env)

        # Apply filters
        if self.provider.filter_chain:
            merged = self._apply_filters(merged, self.provider.filter_chain)

        return merged

    def _apply_filters(
        self, env_map: EnvMap, filter_chain: list[FilterRule | dict[str, str] | str]
    ) -> EnvMap:
        """Apply filter chain to environment map."""
        # Start with empty set and accumulate
        included_keys = set()

        for rule in filter_chain:
            if isinstance(rule, FilterRule):
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
            elif isinstance(rule, dict):
                # Convert dict to FilterRule
                filter_rule = FilterRule(**rule)
                if filter_rule.include:
                    pattern = re.compile(filter_rule.include)
                    for key in env_map:
                        if pattern.match(key):
                            included_keys.add(key)

                if filter_rule.exclude:
                    pattern = re.compile(filter_rule.exclude)
                    for key in list(included_keys):
                        if pattern.match(key):
                            included_keys.discard(key)
            elif isinstance(rule, str):
                # Treat string as include pattern
                pattern = re.compile(rule)
                for key in env_map:
                    if pattern.match(key):
                        included_keys.add(key)

        return {k: v for k, v in env_map.items() if k in included_keys}


class BwsProvider:
    """Bitwarden Secrets Manager provider."""

    def __init__(self, provider: Provider):
        self.id = provider.id
        self.provider = provider

    def load(self, context: RuntimeContext) -> ProviderMap:
        """Load secrets from Bitwarden Secrets Manager."""
        # Expand tokens in vault_url and access_token
        from .token_engine import TokenEngine

        token_engine = TokenEngine(context)
        vault_url = token_engine.expand(self.provider.vault_url or "")
        access_token = token_engine.expand(self.provider.access_token or "")

        if not vault_url or not access_token:
            return self._load_stub_implementation(context)

        return self._load_with_sdk(vault_url, access_token, context)

    def _load_stub_implementation(self, context: RuntimeContext) -> ProviderMap:
        """Load stub implementation when SDK is not available."""
        # Process all environment variables and normalize them
        env_map = {}

        for key, value in context.env.items():
            # Convert to lowercase with hyphens (e.g., BWS_API_KEY -> bws-api-key)
            normalized_key = key.lower().replace("_", "-")
            env_map[normalized_key] = value

        # Apply filters
        if self.provider.filter_chain:
            env_map = self._apply_filters(env_map, self.provider.filter_chain)

        return env_map

    def _load_with_sdk(
        self, vault_url: str, access_token: str, context: RuntimeContext
    ) -> ProviderMap:
        """Load secrets using the Bitwarden SDK."""
        if BitwardenClient is None:
            return self._load_stub_implementation(context)

        try:
            # Initialize client
            settings = ClientSettings(
                api_url=vault_url,
                identity_url=vault_url,
                device_type="CLI",
            )
            client = BitwardenClient(settings)

            # Authenticate
            auth_result = client.auth().login_access_token(access_token)
            if not auth_result.get("success", False):
                raise Exception(
                    f"Authentication failed: {auth_result.get('message', 'Unknown error')}"
                )

            # Extract secret IDs from context
            secret_ids = self._extract_secret_ids_from_context(context)

            # Load secrets
            env_map = {}
            for secret_id in secret_ids:
                try:
                    secret = client.secrets().get(secret_id)
                    if secret:
                        # Use the secret_id as the key (normalized)
                        env_map[secret_id] = secret.value
                except Exception:
                    # Skip secrets that can't be loaded
                    pass

            # Apply filters
            if self.provider.filter_chain:
                env_map = self._apply_filters(env_map, self.provider.filter_chain)

            return env_map

        except Exception:
            # Fall back to stub implementation on error
            return self._load_stub_implementation(context)

    def _extract_secret_ids_from_context(self, context: RuntimeContext) -> list[str]:
        """Extract secret IDs from context (e.g., environment variables)."""
        secret_ids = []

        # Look for environment variables that might contain secret IDs
        for key, value in context.env.items():
            if (
                key.startswith("BWS_SECRET_")
                or key.startswith("BITWARDEN_SECRET_")
                or key == "BWS_SECRET_ID"
                or key == "BITWARDEN_SECRET"
            ) and value:
                secret_ids.append(value)

        return secret_ids

    def _apply_filters(
        self, env_map: EnvMap, filter_chain: list[FilterRule | dict[str, str] | str]
    ) -> EnvMap:
        """Apply filter chain to environment map."""
        # Start with empty set and accumulate
        included_keys = set()

        for rule in filter_chain:
            if isinstance(rule, FilterRule):
                if rule.include:
                    pattern = re.compile(rule.include)
                    for key in env_map:
                        # Convert normalized key back to original format for pattern matching
                        original_key = key.upper().replace("-", "_")
                        if pattern.match(original_key):
                            included_keys.add(key)

                if rule.exclude:
                    pattern = re.compile(rule.exclude)
                    for key in list(included_keys):
                        # Convert normalized key back to original format for pattern matching
                        original_key = key.upper().replace("-", "_")
                        if pattern.match(original_key):
                            included_keys.discard(key)
            elif isinstance(rule, dict):
                # Convert dict to FilterRule
                filter_rule = FilterRule(**rule)
                if filter_rule.include:
                    pattern = re.compile(filter_rule.include)
                    for key in env_map:
                        # Convert normalized key back to original format for pattern matching
                        original_key = key.upper().replace("-", "_")
                        if pattern.match(original_key):
                            included_keys.add(key)

                if filter_rule.exclude:
                    pattern = re.compile(filter_rule.exclude)
                    for key in list(included_keys):
                        # Convert normalized key back to original format for pattern matching
                        original_key = key.upper().replace("-", "_")
                        if pattern.match(original_key):
                            included_keys.discard(key)
            elif isinstance(rule, str):
                # Treat string as include pattern
                pattern = re.compile(rule)
                for key in env_map:
                    # Convert normalized key back to original format for pattern matching
                    original_key = key.upper().replace("-", "_")
                    if pattern.match(original_key):
                        included_keys.add(key)

        return {k: v for k, v in env_map.items() if k in included_keys}


def create_provider(provider: Provider) -> ProviderProtocol:
    """Create a provider instance based on the provider type."""
    if provider.type == "env":
        return EnvProvider(provider)
    elif provider.type == "dotenv":
        return DotenvProvider(provider)
    elif provider.type == "bws":
        return BwsProvider(provider)
    else:
        raise ValueError(f"Unknown provider type: {provider.type}")


def load_providers(spec: Any, context: RuntimeContext) -> ProviderMaps:
    """Load all enabled providers."""
    providers = {}

    for provider_config in spec.configuration_providers:
        if not provider_config.enabled:
            continue

        provider = create_provider(provider_config)
        provider_map = provider.load(context)

        # Mask sensitive values if requested
        if provider_config.mask:
            from .types import MASKED_VALUE

            provider_map = dict.fromkeys(provider_map, MASKED_VALUE)

        providers[provider.id] = provider_map

    return providers
