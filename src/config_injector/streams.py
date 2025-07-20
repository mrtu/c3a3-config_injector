"""Stream management for output redirection and logging."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import RuntimeContext
    from .models import Spec, Stream
    from .token_engine import TokenEngine


@dataclass
class StreamConfig:
    """Configuration for a stream."""

    path: Path | None
    tee_terminal: bool
    append: bool
    format: str


class StreamWriter:
    """Writer for managing output streams."""

    def __init__(
        self,
        stdout_config: StreamConfig | None = None,
        stderr_config: StreamConfig | None = None,
    ):
        self.stdout_config = stdout_config
        self.stderr_config = stderr_config

        self.stdout_file = None
        self.stderr_file = None

        # Sensitive values to mask in output
        self.sensitive_values: list[str] = []

        # Open files if needed
        if self.stdout_config and self.stdout_config.path:
            mode = "a" if self.stdout_config.append else "w"
            self.stdout_file = open(  # noqa: SIM115
                self.stdout_config.path, mode, encoding="utf-8"
            )

        if self.stderr_config and self.stderr_config.path:
            mode = "a" if self.stderr_config.append else "w"
            self.stderr_file = open(  # noqa: SIM115
                self.stderr_config.path, mode, encoding="utf-8"
            )

    def register_sensitive_values(self, values: list[str]) -> None:
        """Register sensitive values that should be masked in output."""
        self.sensitive_values.extend([v for v in values if v])

    def _mask_sensitive_data(self, text: str) -> str:
        """Mask sensitive values in text."""
        from .types import MASKED_VALUE

        if not self.sensitive_values:
            return text

        masked_text = text
        for value in self.sensitive_values:
            if value in masked_text:
                masked_text = masked_text.replace(value, MASKED_VALUE)
        return masked_text

    def write_stdout(self, data: bytes) -> None:
        """Write data to stdout stream."""
        # Decode bytes to string
        text = data.decode("utf-8", errors="replace")

        # Mask sensitive values
        masked_text = self._mask_sensitive_data(text)

        # Write to file if configured
        if self.stdout_file and self.stdout_config:
            if self.stdout_config.format == "json":
                # Write as JSON lines
                for line in masked_text.splitlines():
                    if line.strip():
                        json_line = {
                            "ts": datetime.now().isoformat(),
                            "stream": "stdout",
                            "msg": line.strip(),
                        }
                        self.stdout_file.write(json.dumps(json_line) + "\n")
                        self.stdout_file.flush()
            else:
                # Write as plain text
                self.stdout_file.write(masked_text)
                self.stdout_file.flush()

        # Write to terminal if tee is enabled
        if self.stdout_config and self.stdout_config.tee_terminal:
            sys.stdout.write(masked_text)
            sys.stdout.flush()

    def write_stderr(self, data: bytes) -> None:
        """Write data to stderr stream."""
        # Decode bytes to string
        text = data.decode("utf-8", errors="replace")

        # Mask sensitive values
        masked_text = self._mask_sensitive_data(text)

        # Write to file if configured
        if self.stderr_file and self.stderr_config:
            if self.stderr_config.format == "json":
                # Write as JSON lines
                for line in masked_text.splitlines():
                    if line.strip():
                        json_line = {
                            "ts": datetime.now().isoformat(),
                            "stream": "stderr",
                            "msg": line.strip(),
                        }
                        self.stderr_file.write(json.dumps(json_line) + "\n")
                        self.stderr_file.flush()
            else:
                # Write as plain text
                self.stderr_file.write(masked_text)
                self.stderr_file.flush()

        # Write to terminal if tee is enabled
        if self.stderr_config and self.stderr_config.tee_terminal:
            sys.stderr.write(masked_text)
            sys.stderr.flush()

    def close(self) -> None:
        """Close all open file handles."""
        if self.stdout_file:
            self.stdout_file.close()
        if self.stderr_file:
            self.stderr_file.close()


def prepare_stream(
    stream: Stream | None,
    _context: RuntimeContext,
    token_engine: TokenEngine,
    spec: Spec | None = None,
) -> StreamConfig:
    """Prepare a stream configuration from a Stream model."""
    if stream is None:
        # Use default format from spec if available
        default_format = (
            "json" if spec and spec.default_logging_format == "json" else "text"
        )
        return StreamConfig(
            path=None,
            tee_terminal=False,
            append=False,
            format=default_format,
        )

    path = None
    if stream.path:
        # Expand tokens in the path
        expanded_path = token_engine.expand(stream.path)
        path = Path(expanded_path)

    # Use default_logging_format from spec if stream format is the default "text"
    format_to_use = stream.format
    if stream.format == "text" and spec and spec.default_logging_format:
        format_to_use = spec.default_logging_format

    return StreamConfig(
        path=path,
        tee_terminal=stream.tee_terminal,
        append=stream.append,
        format=format_to_use,
    )
