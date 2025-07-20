"""Tests for the streams module."""

import io
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from config_injector.core import RuntimeContext
from config_injector.models import Spec, Stream, Target
from config_injector.streams import StreamConfig, StreamWriter, prepare_stream
from config_injector.token_engine import TokenEngine


def test_stream_config():
    """Test StreamConfig creation."""
    config = StreamConfig(
        path=Path("/tmp/test.log"), tee_terminal=True, append=False, format="text"
    )

    assert config.path == Path("/tmp/test.log")
    assert config.tee_terminal is True
    assert config.append is False
    assert config.format == "text"


def test_prepare_stream():
    """Test prepare_stream function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a stream model
        stream = Stream(
            path="${HOME}/test.log", tee_terminal=True, append=False, format="text"
        )

        # Create a runtime context
        context = RuntimeContext(
            env={},
            now=None,
            pid=12345,
            home=tmpdir,  # Use temporary directory as HOME
            seq=1,
        )

        # Create a token engine
        token_engine = TokenEngine(context)

        # Prepare the stream
        config = prepare_stream(stream, context, token_engine)

        assert config.path == Path(f"{tmpdir}/test.log").resolve()
        assert config.tee_terminal is True
        assert config.append is False
        assert config.format == "text"


def test_prepare_stream_with_complex_tokens():
    """Test prepare_stream function with complex tokens."""
    from datetime import datetime

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a stream model with complex tokens
        stream = Stream(
            path="${HOME}/logs/${DATE:%Y-%m-%d}/${PID}_${SEQ}_${UUID}.log",
            tee_terminal=True,
            append=False,
            format="text",
        )

        # Create a runtime context with a fixed datetime for testing
        test_date = datetime(2023, 1, 1, 12, 0, 0)
        context = RuntimeContext(
            env={},
            now=test_date,
            pid=12345,
            home=tmpdir,  # Use temporary directory as HOME
            seq=42,
        )

        # Create a token engine
        token_engine = TokenEngine(context)

        # Prepare the stream
        config = prepare_stream(stream, context, token_engine)

        # Check that the path has the expected format
        path_str = str(config.path)
        expected_prefix = f"{tmpdir}/logs/2023-01-01/12345_0042_"
        assert path_str.startswith(expected_prefix)
        assert path_str.endswith(".log")

        # Extract just the filename and check the PID_SEQ_UUID pattern
        filename = Path(path_str).name  # Get just the filename part
        filename_without_ext = filename.rsplit(".", 1)[0]  # Remove .log extension
        filename_parts = filename_without_ext.split("_")
        assert len(filename_parts) == 3  # PID, SEQ, UUID

        # UUID should be in the path
        # Extract the part between the prefix and the .log extension
        uuid_part = path_str[len(expected_prefix) :].split(".")[0]
        # UUID should be a valid UUID (standard length is 36 characters)
        assert len(uuid_part) >= 36  # UUID might contain additional characters

        assert config.tee_terminal is True
        assert config.append is False
        assert config.format == "text"


def test_prepare_stream_with_none():
    """Test prepare_stream function with None stream."""
    # Create a runtime context
    context = RuntimeContext(env={}, now=None, pid=12345, home="/home/user", seq=1)

    # Create a token engine
    token_engine = TokenEngine(context)

    # Prepare the stream with None
    config = prepare_stream(None, context, token_engine)

    assert config.path is None
    assert config.tee_terminal is False
    assert config.append is False
    assert config.format == "text"


def test_prepare_stream_with_default_format():
    """Test prepare_stream function with default_logging_format in spec."""

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a stream model with no format specified
        stream = Stream(path="${HOME}/test.log", tee_terminal=True, append=False)

        # Create a spec with default_logging_format
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[],
            target=Target(working_dir="/tmp", command=["echo", "test"]),
            default_logging_format="json",
        )

        # Create a runtime context
        context = RuntimeContext(
            env={},
            now=None,
            pid=12345,
            home=tmpdir,  # Use temporary directory as HOME
            seq=1,
        )

        # Create a token engine
        token_engine = TokenEngine(context)

        # Prepare the stream with spec
        config = prepare_stream(stream, context, token_engine, spec)

        assert config.path == Path(f"{tmpdir}/test.log").resolve()
        assert config.tee_terminal is True
        assert config.append is False
        # Should use the default_logging_format from spec
        assert config.format == "json"


def test_stream_writer_file_output():
    """Test StreamWriter writing to file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a temporary file path
        temp_file = Path(tmpdir) / "test.log"

        # Create a stream config
        config = StreamConfig(
            path=temp_file, tee_terminal=False, append=False, format="text"
        )

        # Create a stream writer
        writer = StreamWriter(stdout_config=config)

        try:
            # Write some data
            writer.write_stdout(b"Hello, world!\n")

            # Close the writer
            writer.close()

            # Check that the file was created and contains the expected data
            assert temp_file.exists()
            assert temp_file.read_text() == "Hello, world!\n"
        finally:
            # Clean up
            writer.close()


def test_stream_writer_tee_terminal():
    """Test StreamWriter teeing to terminal."""
    # Create a stream config with tee_terminal=True
    config = StreamConfig(path=None, tee_terminal=True, append=False, format="text")

    # Create a mock buffer
    mock_buffer = io.BytesIO()

    # Create a stream writer
    writer = StreamWriter(stdout_config=config)

    # Patch sys.stdout.buffer to use our mock buffer
    with (
        patch("sys.stdout.buffer.write", mock_buffer.write),
        patch("sys.stdout.buffer.flush"),
    ):
        # Write some data
        writer.write_stdout(b"Hello, world!\n")

        # Check that the data was written to our mock buffer
        assert mock_buffer.getvalue() == b"Hello, world!\n"


def test_stream_writer_sensitive_data():
    """Test StreamWriter masking sensitive data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a temporary file path
        temp_file = Path(tmpdir) / "test.log"

        # Create a stream config
        config = StreamConfig(
            path=temp_file, tee_terminal=False, append=False, format="text"
        )

        # Create a stream writer
        writer = StreamWriter(stdout_config=config)

        try:
            # Register sensitive values
            writer.register_sensitive_values(["SECRET"])

            # Write some data with sensitive information
            writer.write_stdout(b"This is a SECRET message\n")

            # Close the writer
            writer.close()

            # Check that the file was created and contains masked data
            assert temp_file.exists()
            assert "SECRET" not in temp_file.read_text()
            assert "<masked>" in temp_file.read_text()
        finally:
            # Clean up
            writer.close()


def test_stream_writer_json_format():
    """Test StreamWriter with JSON format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a temporary file path
        temp_file = Path(tmpdir) / "test.log"

        # Create a stream config
        config = StreamConfig(
            path=temp_file, tee_terminal=False, append=False, format="json"
        )

        # Create a stream writer
        writer = StreamWriter(stdout_config=config)

        try:
            # Write some data
            writer.write_stdout(b"Hello, world!\n")

            # Close the writer
            writer.close()

            # Check that the file was created and contains JSON data
            assert temp_file.exists()
            content = temp_file.read_text()
            assert "Hello, world!" in content
            assert "ts" in content
            assert "stream" in content
            assert "stdout" in content
        finally:
            # Clean up
            writer.close()


if __name__ == "__main__":
    pytest.main([__file__])
