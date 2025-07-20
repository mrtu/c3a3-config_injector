"""Token engine for expanding ${...} expressions in configuration values."""

from __future__ import annotations

import re
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import RuntimeContext
    from .types import ProviderMaps


class TokenEngine:
    """Engine for expanding ${...} tokens in strings."""

    def __init__(self, context: RuntimeContext, provider_maps: ProviderMaps | None = None):
        self.context = context
        self.provider_maps = provider_maps or {}

    def expand(self, template: str) -> str:
        """Expand all tokens in a template string."""
        value, warnings = self.try_expand(template)
        if warnings:
            # For now, just log warnings. In the future, we might want to raise exceptions
            pass
        return value

    def try_expand(self, template: str) -> tuple[str, list[str]]:
        """Expand tokens and return value with warnings."""
        warnings = []
        result = template

        # Find all ${...} tokens
        token_pattern = r"\$\{([^}]+)\}"
        matches = re.finditer(token_pattern, result)

        for match in matches:
            token_content = match.group(1)
            expanded_value, token_warnings = self._expand_token(token_content)
            warnings.extend(token_warnings)

            # Replace the token with its expanded value
            result = result.replace(match.group(0), str(expanded_value))

        return result, warnings

    def _expand_token(self, token_content: str) -> tuple[str, list[str]]:
        """Expand a single token."""
        warnings = []

        # Handle fallback syntax: ${TOKEN|fallback}
        if "|" in token_content:
            token_part, fallback = token_content.split("|", 1)
            value, token_warnings = self._expand_single_token(token_part.strip())
            warnings.extend(token_warnings)

            if value is None or value == "":
                return fallback.strip(), warnings
            return value, warnings

        return self._expand_single_token(token_content)

    def _expand_single_token(self, token: str) -> tuple[str, list[str]]:
        """Expand a single token without fallback."""
        warnings = []

        # Environment variables: ${ENV:VAR}
        if token.startswith("ENV:"):
            var_name = token[4:]
            value = self.context.env.get(var_name)
            if value is None:
                warnings.append(f"Environment variable '{var_name}' not found")
                return "", warnings
            return value, warnings

        # Provider values: ${PROVIDER:id:key}
        if token.startswith("PROVIDER:"):
            parts = token[9:].split(":", 1)
            if len(parts) != 2:
                warnings.append(f"Invalid provider token format: {token}")
                return "", warnings

            provider_id, key = parts
            if provider_id not in self.provider_maps:
                warnings.append(f"Provider '{provider_id}' not found")
                return "", warnings

            value = self.provider_maps[provider_id].get(key)
            if value is None:
                warnings.append(f"Key '{key}' not found in provider '{provider_id}'")
                return "", warnings
            return value, warnings

        # Date tokens: ${DATE:format}
        if token.startswith("DATE:"):
            format_str = token[5:]
            try:
                return self.context.now.strftime(format_str), warnings
            except Exception as e:
                warnings.append(f"Invalid date format '{format_str}': {e}")
                return "", warnings

        # Time tokens: ${TIME:format}
        if token.startswith("TIME:"):
            format_str = token[5:]
            try:
                return self.context.now.strftime(format_str), warnings
            except Exception as e:
                warnings.append(f"Invalid time format '{format_str}': {e}")
                return "", warnings

        # Special tokens
        if token == "HOME":
            return self.context.home, warnings

        if token == "PID":
            return str(self.context.pid), warnings

        if token == "UUID":
            return str(uuid.uuid4()), warnings

        if token == "SEQ":
            return f"{self.context.seq:04d}", warnings

        # Unknown token
        warnings.append(f"Unknown token: {token}")
        return "", warnings
