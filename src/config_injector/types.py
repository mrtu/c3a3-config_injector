"""Type definitions for the Configuration Wrapping Framework."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# Constants
MASKED_VALUE = "<masked>"


# Utility functions
def mask_sensitive_value(
    value: str | bytes | None, is_sensitive: bool
) -> str | bytes | None:
    """Mask a sensitive value with a placeholder.

    Args:
        value: The value to potentially mask
        is_sensitive: Whether the value should be masked

    Returns:
        The original value if not sensitive, or a masked placeholder if sensitive
    """
    if value is None or not is_sensitive:
        return value

    if isinstance(value, bytes):
        return MASKED_VALUE.encode("utf-8")
    return MASKED_VALUE


# Type aliases
EnvMap = dict[str, str]
ProviderMap = dict[str, str]
ProviderMaps = dict[str, ProviderMap]
Argv = list[str]
Errors = list[str]


@dataclass
class RuntimeContext:
    """Runtime context for token expansion and provider resolution."""

    env: EnvMap
    now: datetime
    pid: int
    home: str
    seq: int  # incremented per invocation
    extra: dict[str, Any] = field(default_factory=dict)
