"""Pydantic models for the Configuration Wrapping Framework."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional, Union
from pathlib import Path

from pydantic import BaseModel, Field, AnyUrl, field_validator, model_validator


class FilterRule(BaseModel):
    """Filter rule for provider key filtering."""

    include: Optional[str] = None
    exclude: Optional[str] = None

    @field_validator('include', 'exclude')
    @classmethod
    def _compile_regex(cls, v: Optional[str]) -> Optional[str]:
        """Validate and compile regex patterns."""
        if v is None:
            return v
        try:
            re.compile(v)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{v}': {e}")
        return v


class Provider(BaseModel):
    """Configuration provider definition."""

    type: Literal['env', 'dotenv', 'bws', 'custom']
    id: str
    name: Optional[str] = None
    enabled: bool = True
    passthrough: bool = False
    mask: bool = False
    hierarchical: Optional[bool] = None
    filename: Optional[str] = None
    path: Optional[str] = None
    precedence: Optional[str] = None  # e.g., deep-first
    vault_url: Optional[str] = None
    access_token: Optional[str] = None
    filter_chain: List[Union[FilterRule, Dict[str, str], str]] = Field(default_factory=list)

    @model_validator(mode='after')
    def _normalize_filter_chain(self):
        """Convert filter_chain items to FilterRule objects."""
        normalized_chain = []
        for item in self.filter_chain:
            if isinstance(item, FilterRule):
                normalized_chain.append(item)
            elif isinstance(item, dict):
                normalized_chain.append(FilterRule(**item))
            elif isinstance(item, str):
                # Treat string as include pattern
                normalized_chain.append(FilterRule(include=item))
            else:
                raise ValueError(f"Invalid filter_chain item: {item}")
        self.filter_chain = normalized_chain
        return self


class Injector(BaseModel):
    """Configuration injector definition."""

    name: str
    kind: Literal['env_var', 'named', 'positional', 'file', 'stdin_fragment']
    aliases: List[str] = Field(default_factory=list)
    sources: List[Any] = Field(default_factory=list)  # strings after interpolation
    precedence: str = 'first_non_empty'
    required: bool = False
    default: Optional[Any] = None
    type: Optional[Literal['string', 'int', 'bool', 'path', 'list', 'json']] = None
    sensitive: bool = False
    when: Optional[str] = None
    order: Optional[int] = None
    connector: Optional[Literal['=', 'space', 'repeat']] = '='
    delimiter: str = ','  # Delimiter for list type coercion


class Stream(BaseModel):
    """Output stream configuration."""

    path: Optional[str] = None
    tee_terminal: bool = False
    append: bool = False
    format: Literal['text', 'json'] = 'text'


class Target(BaseModel):
    """Target execution configuration."""

    working_dir: str
    shell: Optional[Literal['bash', 'sh', 'powershell', 'none']] = 'none'
    command: List[str]
    stdin: Optional[str] = None
    stdout: Stream = Field(default_factory=Stream)
    stderr: Stream = Field(default_factory=Stream)


class Spec(BaseModel):
    """Main configuration specification."""

    version: str
    env_passthrough: bool = False
    default_logging_format: Optional[Literal['text', 'json']] = None
    mask_defaults: bool = False
    configuration_providers: List[Provider]
    configuration_injectors: List[Injector]
    target: Target
    profiles: Optional[Dict[str, Any]] = None    # extension
    validation: Optional[Dict[str, Any]] = None  # extension 
