"""Configuration models for the Configuration Wrapping Framework."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class FilterRule(BaseModel):
    """Filter rule for provider key filtering."""

    include: str | None = None
    exclude: str | None = None

    @field_validator("include", "exclude")
    @classmethod
    def _compile_regex(cls, v: str | None) -> str | None:
        """Validate and compile regex patterns."""
        if v is None:
            return v
        try:
            re.compile(v)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{v}': {e}") from e
        return v


class Provider(BaseModel):
    """Configuration provider definition."""

    type: Literal["env", "dotenv", "bws", "custom"]
    id: str
    name: str | None = None
    enabled: bool = True
    passthrough: bool = False
    mask: bool = False
    hierarchical: bool | None = None
    filename: str | None = None
    path: str | None = None
    precedence: str | None = None  # e.g., deep-first
    vault_url: str | None = None
    access_token: str | None = None
    filter_chain: list[FilterRule | dict[str, str] | str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _normalize_filter_chain(self) -> Provider:
        """Convert filter_chain items to FilterRule objects."""
        normalized_chain: list[FilterRule] = []
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
        # Cast to the expected type to avoid mypy issues
        self.filter_chain = normalized_chain  # type: ignore[assignment]
        return self


class Injector(BaseModel):
    """Configuration injector definition."""

    name: str
    kind: Literal["env_var", "named", "positional", "file", "stdin_fragment"]
    aliases: list[str] = Field(default_factory=list)
    sources: list[Any] = Field(default_factory=list)  # strings after interpolation
    precedence: str = "first_non_empty"
    required: bool = False
    default: Any | None = None
    type: Literal["string", "int", "bool", "path", "list", "json"] | None = None
    sensitive: bool = False
    when: str | None = None
    order: int | None = None
    connector: Literal["=", "space", "repeat"] | None = "="
    delimiter: str = ","  # Delimiter for list type coercion


class Stream(BaseModel):
    """Output stream configuration."""

    path: str | None = None
    tee_terminal: bool = False
    append: bool = False
    format: Literal["text", "json"] = "text"


class Target(BaseModel):
    """Target execution configuration."""

    working_dir: str
    shell: Literal["bash", "sh", "powershell", "none"] | None = "none"
    command: list[str]
    stdin: str | None = None
    stdout: Stream = Field(default_factory=Stream)
    stderr: Stream = Field(default_factory=Stream)


class Spec(BaseModel):
    """Main configuration specification."""

    version: str
    env_passthrough: bool = False
    default_logging_format: Literal["text", "json"] | None = None
    mask_defaults: bool = False
    configuration_providers: list[Provider]
    configuration_injectors: list[Injector]
    target: Target
    profiles: dict[str, Any] | None = None  # extension
    validation: dict[str, Any] | None = None  # extension
