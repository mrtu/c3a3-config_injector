"""Type definitions for the Configuration Wrapping Framework."""

from typing import Dict, List, Any, Union
from dataclasses import dataclass, field
from datetime import datetime

# Constants
MASKED_VALUE = "<masked>"

# Utility functions
def mask_sensitive_value(value: Union[str, bytes, None], is_sensitive: bool) -> Union[str, bytes, None]:
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
        return MASKED_VALUE.encode('utf-8')
    return MASKED_VALUE

# Type aliases
EnvMap = Dict[str, str]
ProviderMap = Dict[str, str]
ProviderMaps = Dict[str, ProviderMap]
Argv = List[str]
Errors = List[str]

@dataclass
class RuntimeContext:
    """Runtime context for token expansion and provider resolution."""

    env: EnvMap
    now: datetime
    pid: int
    home: str
    seq: int  # incremented per invocation
    extra: Dict[str, Any] = field(default_factory=dict)
