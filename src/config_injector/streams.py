"""Stream management for output redirection and logging."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .core import RuntimeContext
from .types import EnvMap
from .models import Stream
from .token_engine import TokenEngine


@dataclass
class StreamConfig:
    """Configuration for a stream."""

    path: Optional[Path]
    tee_terminal: bool
    append: bool
    format: str


class StreamWriter:
    """Writer for managing output streams."""

    def __init__(self, stdout_config: Optional[StreamConfig] = None, stderr_config: Optional[StreamConfig] = None):
        self.stdout_config = stdout_config
        self.stderr_config = stderr_config

        self.stdout_file = None
        self.stderr_file = None

        # Sensitive values to mask in output
        self.sensitive_values = []

        # Open files if needed
        if self.stdout_config and self.stdout_config.path:
            mode = 'a' if self.stdout_config.append else 'w'
            self.stdout_file = open(self.stdout_config.path, mode, encoding='utf-8')

        if self.stderr_config and self.stderr_config.path:
            mode = 'a' if self.stderr_config.append else 'w'
            self.stderr_file = open(self.stderr_config.path, mode, encoding='utf-8')

    def register_sensitive_values(self, values: List[str]) -> None:
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
        text = data.decode('utf-8', errors='replace')

        # Mask sensitive values
        masked_text = self._mask_sensitive_data(text)

        # Write to file if configured
        if self.stdout_file:
            if self.stdout_config.format == 'json':
                # Write as JSON lines
                for line in masked_text.splitlines():
                    if line.strip():
                        json_line = {
                            'ts': datetime.now().isoformat(),
                            'stream': 'stdout',
                            'msg': line.strip(),
                        }
                        self.stdout_file.write(json.dumps(json_line) + '\n')
                        self.stdout_file.flush()
            else:
                # Write as plain text
                self.stdout_file.write(masked_text)
                self.stdout_file.flush()

        # Write to terminal if tee is enabled
        if self.stdout_config and self.stdout_config.tee_terminal:
            # Convert masked text back to bytes
            masked_data = masked_text.encode('utf-8')
            sys.stdout.buffer.write(masked_data)
            sys.stdout.buffer.flush()

    def write_stderr(self, data: bytes) -> None:
        """Write data to stderr stream."""
        # Decode bytes to string
        text = data.decode('utf-8', errors='replace')

        # Mask sensitive values
        masked_text = self._mask_sensitive_data(text)

        # Write to file if configured
        if self.stderr_file:
            if self.stderr_config.format == 'json':
                # Write as JSON lines
                for line in masked_text.splitlines():
                    if line.strip():
                        json_line = {
                            'ts': datetime.now().isoformat(),
                            'stream': 'stderr',
                            'msg': line.strip(),
                        }
                        self.stderr_file.write(json.dumps(json_line) + '\n')
                        self.stderr_file.flush()
            else:
                # Write as plain text
                self.stderr_file.write(masked_text)
                self.stderr_file.flush()

        # Write to terminal if tee is enabled
        if self.stderr_config and self.stderr_config.tee_terminal:
            # Convert masked text back to bytes
            masked_data = masked_text.encode('utf-8')
            sys.stderr.buffer.write(masked_data)
            sys.stderr.buffer.flush()

    def close(self) -> None:
        """Close all file handles."""
        if self.stdout_file:
            self.stdout_file.close()
            self.stdout_file = None

        if self.stderr_file:
            self.stderr_file.close()
            self.stderr_file = None


def prepare_stream(stream: Stream, context: RuntimeContext, token_engine: TokenEngine, spec=None) -> StreamConfig:
    """Prepare stream configuration by expanding tokens in path.

    Supports collision-safe naming using the following tokens:
    - ${PID} - Process ID (e.g., "12345")
    - ${SEQ} - Sequence number, incremented per invocation (e.g., "0001")
    - ${UUID} - Universally unique identifier (e.g., "550e8400-e29b-41d4-a716-446655440000")
    - ${DATE:format} - Current date with specified format (e.g., "${DATE:%Y%m%d}" -> "20230405")
    - ${TIME:format} - Current time with specified format (e.g., "${TIME:%H%M%S}" -> "142536")

    Examples of collision-safe naming patterns:
    - "logs/app-${PID}.log" - Use process ID to avoid collisions between processes
    - "logs/app-${SEQ}.log" - Use sequence number for sequential files
    - "logs/app-${DATE:%Y%m%d}-${TIME:%H%M%S}.log" - Use timestamp for time-based naming
    - "logs/app-${UUID}.log" - Use UUID for guaranteed uniqueness
    - "logs/app-${PID}-${SEQ}.log" - Combine PID and sequence for process-specific sequences
    """
    path = None
    if stream and stream.path:
        expanded_path = token_engine.expand(stream.path)
        path = Path(expanded_path).expanduser().resolve()

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

    # Use the stream's format if specified, otherwise use the spec's default_logging_format if available
    format = "text"
    if stream and hasattr(stream, 'format') and stream.format != "text":
        format = stream.format
    elif spec and spec.default_logging_format:
        format = spec.default_logging_format

    return StreamConfig(
        path=path,
        tee_terminal=stream.tee_terminal if stream else False,
        append=stream.append if stream else False,
        format=format,
    ) 
