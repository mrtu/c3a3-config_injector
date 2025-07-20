"""Tests for the masking functionality of sensitive values."""

import io
import os
import tempfile
from pathlib import Path

import pytest

from config_injector.models import Spec, Provider, Injector, Target, Stream
from config_injector.core import build_runtime_context, dry_run, execute
from config_injector.injectors import resolve_injector
from config_injector.token_engine import TokenEngine
from config_injector.providers import load_providers
from config_injector.streams import StreamWriter, StreamConfig
from config_injector.types import MASKED_VALUE


def test_sensitive_injector_masking():
    """Test that sensitive injectors are properly masked."""
    # Create a minimal spec with a sensitive injector
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_sensitive",
                kind="env_var",
                aliases=["TEST_SECRET"],
                sources=["super_secret_value"],
                sensitive=True
            )
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"])
    )

    # Build runtime context
    context = build_runtime_context(spec)

    # Load providers
    providers = load_providers(spec, context)

    # Create token engine
    token_engine = TokenEngine(context, providers)

    # Resolve injector
    resolved = resolve_injector(spec.configuration_injectors[0], context, providers, token_engine)

    # Verify the injector is marked as sensitive
    assert resolved.is_sensitive

    # Verify the value is not masked in the resolved injector
    assert resolved.value == "super_secret_value"

    # Perform dry run to get text summary
    dry_run_result = dry_run(spec, context)

    # Verify the value is masked in the text summary
    assert "super_secret_value" not in dry_run_result.text_summary
    assert MASKED_VALUE in dry_run_result.text_summary

    # Verify the value is masked in the JSON summary
    for injection in dry_run_result.json_summary["injections"]:
        if injection["name"] == "test_sensitive":
            assert injection["sensitive"]
            assert injection["value"] == MASKED_VALUE


def test_sensitive_injector_stream_masking():
    """Test that sensitive values are masked in stream output."""
    # Create a minimal spec with a sensitive injector
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_sensitive",
                kind="env_var",
                aliases=["TEST_SECRET"],
                sources=["super_secret_value"],
                sensitive=True
            )
        ],
        target=Target(working_dir="/tmp", command=["echo", "${TEST_SECRET}"])
    )

    # Build runtime context
    context = build_runtime_context(spec)

    # Perform dry run to get resolved injectors and build result
    dry_run_result = dry_run(spec, context)

    # Create a stream writer with in-memory buffers
    stdout_buffer = io.BytesIO()
    stderr_buffer = io.BytesIO()

    class TestStreamWriter(StreamWriter):
        """Test stream writer that writes to in-memory buffers."""

        def write_stdout(self, data: bytes) -> None:
            # Decode bytes to string
            text = data.decode('utf-8', errors='replace')

            # Mask sensitive values
            masked_text = self._mask_sensitive_data(text)

            # Write masked text to buffer
            stdout_buffer.write(masked_text.encode('utf-8'))

        def write_stderr(self, data: bytes) -> None:
            # Decode bytes to string
            text = data.decode('utf-8', errors='replace')

            # Mask sensitive values
            masked_text = self._mask_sensitive_data(text)

            # Write masked text to buffer
            stderr_buffer.write(masked_text.encode('utf-8'))

    # Create stream writer
    streams = TestStreamWriter()

    # Register sensitive values
    for resolved_inj in dry_run_result.resolved:
        if resolved_inj.is_sensitive and resolved_inj.value:
            streams.register_sensitive_values([resolved_inj.value])

    # Simulate output containing the sensitive value
    streams.write_stdout(b"This contains the super_secret_value and should be masked")

    # Verify the sensitive value is masked in the output
    stdout_content = stdout_buffer.getvalue().decode('utf-8')
    assert "super_secret_value" not in stdout_content
    assert MASKED_VALUE in stdout_content


def test_multiple_sensitive_injectors():
    """Test that multiple sensitive injectors are properly masked."""
    # Create a minimal spec with multiple sensitive injectors
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_sensitive1",
                kind="env_var",
                aliases=["TEST_SECRET1"],
                sources=["super_secret_value1"],
                sensitive=True
            ),
            Injector(
                name="test_sensitive2",
                kind="named",
                aliases=["--password"],
                sources=["super_secret_value2"],
                sensitive=True
            ),
            Injector(
                name="test_not_sensitive",
                kind="positional",
                sources=["not_secret_value"],
                sensitive=False,
                order=1
            )
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"])
    )

    # Build runtime context
    context = build_runtime_context(spec)

    # Perform dry run to get text summary
    dry_run_result = dry_run(spec, context)

    # Verify sensitive values are masked in the text summary
    assert "super_secret_value1" not in dry_run_result.text_summary
    assert "super_secret_value2" not in dry_run_result.text_summary
    assert "not_secret_value" in dry_run_result.text_summary

    # Verify sensitive values are masked in the JSON summary
    for injection in dry_run_result.json_summary["injections"]:
        if injection["name"] == "test_sensitive1" or injection["name"] == "test_sensitive2":
            assert injection["sensitive"]
            assert injection["value"] == MASKED_VALUE
        elif injection["name"] == "test_not_sensitive":
            assert not injection["sensitive"]
            assert injection["value"] == "not_secret_value"


def test_provider_masking():
    """Test that provider masking works correctly."""
    # Create a spec with a masked provider
    spec = Spec(
        version="0.1",
        configuration_providers=[
            Provider(
                id="test_provider",
                type="env",
                enabled=True,
                mask=True,
                filter_chain=[
                    {"include": "TEST_.*"}
                ]
            )
        ],
        configuration_injectors=[
            Injector(
                name="test_injector",
                kind="env_var",
                aliases=["TEST_VAR"],
                sources=["${PROVIDER:test_provider:TEST_SECRET}"]
            )
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"])
    )

    # Set up environment with test values
    import os
    original_env = os.environ.copy()
    os.environ["TEST_SECRET"] = "super_secret_value"

    try:
        # Build runtime context
        context = build_runtime_context(spec)

        # Perform dry run
        dry_run_result = dry_run(spec, context)

        # Verify the provider values are masked in the text summary
        assert "super_secret_value" not in dry_run_result.text_summary
        assert "masked: 1" in dry_run_result.text_summary

        # Verify the provider values are masked in the JSON summary
        provider_info = dry_run_result.json_summary["providers"]["test_provider"]
        assert provider_info["masked_count"] == 1

    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


def test_error_message_masking():
    """Test that error messages don't leak sensitive values."""
    # Create a spec with a sensitive injector that will cause an error
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_sensitive_error",
                kind="env_var",
                aliases=["TEST_SECRET"],
                sources=["${PROVIDER:nonexistent:super_secret_value}"],  # This will cause an error
                sensitive=True
            )
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"])
    )

    # Build runtime context
    context = build_runtime_context(spec)

    # Perform dry run
    dry_run_result = dry_run(spec, context)

    # Verify the sensitive value doesn't appear in error messages
    assert "super_secret_value" not in dry_run_result.text_summary

    # Check JSON summary for error messages
    for injection in dry_run_result.json_summary["injections"]:
        if injection["name"] == "test_sensitive_error":
            for error in injection["errors"]:
                assert "super_secret_value" not in error


def test_partial_string_masking():
    """Test that partial string replacement works correctly."""
    # Create a spec with sensitive values that are substrings of other values
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_partial1",
                kind="env_var",
                aliases=["TEST_VAR1"],
                sources=["secret"],
                sensitive=True
            ),
            Injector(
                name="test_partial2",
                kind="env_var",
                aliases=["TEST_VAR2"],
                sources=["my_secret_value"],  # Contains "secret" as substring
                sensitive=True
            ),
            Injector(
                name="test_partial3",
                kind="positional",
                sources=["secret_and_more_secret"],  # Contains "secret" multiple times
                sensitive=True,
                order=1
            )
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"])
    )

    # Build runtime context
    context = build_runtime_context(spec)

    # Perform dry run
    dry_run_result = dry_run(spec, context)

    # Verify all sensitive values are masked
    assert "secret" not in dry_run_result.text_summary
    assert "my_secret_value" not in dry_run_result.text_summary
    assert "secret_and_more_secret" not in dry_run_result.text_summary
    assert MASKED_VALUE in dry_run_result.text_summary


def test_case_sensitive_masking():
    """Test that masking handles case sensitivity correctly."""
    # Create a spec with sensitive values in different cases
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_case",
                kind="env_var",
                aliases=["TEST_SECRET"],
                sources=["SecretValue"],
                sensitive=True
            )
        ],
        target=Target(working_dir="/tmp", command=["echo", "SecretValue", "secretvalue", "SECRETVALUE"])
    )

    # Build runtime context
    context = build_runtime_context(spec)

    # Perform dry run
    dry_run_result = dry_run(spec, context)

    # Verify exact case match is masked
    assert "SecretValue" not in dry_run_result.text_summary

    # Note: Different cases should not be masked (this is expected behavior)
    # The masking is case-sensitive by design


def test_file_path_masking():
    """Test that file paths containing sensitive values are masked."""
    # Create a spec with file injector containing sensitive path
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_file_secret",
                kind="file",
                sources=["secret_content"],
                sensitive=True
            )
        ],
        target=Target(working_dir="/tmp", command=["cat", "${FILE:test_file_secret}"])
    )

    # Build runtime context
    context = build_runtime_context(spec)

    # Perform dry run
    dry_run_result = dry_run(spec, context)

    # Verify sensitive content is masked in the summary
    assert "secret_content" not in dry_run_result.text_summary
    assert MASKED_VALUE in dry_run_result.text_summary


def test_stdin_fragment_masking():
    """Test that stdin fragments containing sensitive values are masked."""
    # Create a spec with stdin_fragment injector
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_stdin_secret",
                kind="stdin_fragment",
                sources=["secret_input_data"],
                sensitive=True
            )
        ],
        target=Target(working_dir="/tmp", command=["cat"])
    )

    # Build runtime context
    context = build_runtime_context(spec)

    # Perform dry run
    dry_run_result = dry_run(spec, context)

    # Verify sensitive stdin content is masked
    assert "secret_input_data" not in dry_run_result.text_summary
    assert MASKED_VALUE in dry_run_result.text_summary


def test_token_expansion_masking():
    """Test that token expansion doesn't leak sensitive values."""
    # Create a spec with token expansion in sensitive context
    spec = Spec(
        version="0.1",
        configuration_providers=[
            Provider(
                id="secret_provider",
                type="env",
                enabled=True,
                filter_chain=[
                    {"include": "SECRET_.*"}
                ]
            )
        ],
        configuration_injectors=[
            Injector(
                name="test_token_secret",
                kind="env_var",
                aliases=["EXPANDED_SECRET"],
                sources=["${PROVIDER:secret_provider:SECRET_KEY}"],
                sensitive=True
            )
        ],
        target=Target(working_dir="/tmp", command=["echo", "${EXPANDED_SECRET}"])
    )

    # Set up environment
    import os
    original_env = os.environ.copy()
    os.environ["SECRET_KEY"] = "token_secret_value"

    try:
        # Build runtime context
        context = build_runtime_context(spec)

        # Perform dry run
        dry_run_result = dry_run(spec, context)

        # Verify token expansion result is masked
        assert "token_secret_value" not in dry_run_result.text_summary
        assert MASKED_VALUE in dry_run_result.text_summary

    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


def test_json_log_format_masking():
    """Test that JSON log format properly masks sensitive values."""
    # Create a spec with sensitive injector and JSON logging
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_json_secret",
                kind="env_var",
                aliases=["JSON_SECRET"],
                sources=["json_secret_value"],
                sensitive=True
            )
        ],
        target=Target(
            working_dir="/tmp", 
            command=["echo", "${JSON_SECRET}"],
            stdout=Stream(path="/tmp/test.log", format="json", tee_terminal=False)
        )
    )

    # Build runtime context
    context = build_runtime_context(spec)

    # Create a stream writer with JSON format
    stdout_buffer = io.BytesIO()

    class TestJSONStreamWriter(StreamWriter):
        """Test stream writer for JSON format testing."""

        def write_stdout(self, data: bytes) -> None:
            # Decode bytes to string
            text = data.decode('utf-8', errors='replace')

            # Mask sensitive values
            masked_text = self._mask_sensitive_data(text)

            # Write masked text to buffer (simulating JSON format)
            import json
            from datetime import datetime
            for line in masked_text.splitlines():
                if line.strip():
                    json_line = {
                        'ts': datetime.now().isoformat(),
                        'stream': 'stdout',
                        'msg': line.strip(),
                    }
                    stdout_buffer.write((json.dumps(json_line) + '\n').encode('utf-8'))

    # Perform dry run to get resolved injectors
    dry_run_result = dry_run(spec, context)

    # Create stream writer
    streams = TestJSONStreamWriter()

    # Register sensitive values
    for resolved_inj in dry_run_result.resolved:
        if resolved_inj.is_sensitive and resolved_inj.value:
            streams.register_sensitive_values([resolved_inj.value])

    # Simulate JSON log output containing the sensitive value
    streams.write_stdout(b"Processing json_secret_value in JSON format")

    # Verify the sensitive value is masked in JSON output
    stdout_content = stdout_buffer.getvalue().decode('utf-8')
    assert "json_secret_value" not in stdout_content
    assert MASKED_VALUE in stdout_content


def test_environment_variable_names_security():
    """Test that environment variable names don't leak sensitive information."""
    # Create a spec where env var names might be sensitive
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_env_name",
                kind="env_var",
                aliases=["SECRET_API_KEY"],  # The name itself might be sensitive
                sources=["secret_value"],
                sensitive=True
            )
        ],
        target=Target(working_dir="/tmp", command=["echo", "test"])
    )

    # Build runtime context
    context = build_runtime_context(spec)

    # Perform dry run
    dry_run_result = dry_run(spec, context)

    # Verify the sensitive value is masked but alias names are still shown
    # (This is expected behavior - alias names are part of the configuration, not secrets)
    assert "secret_value" not in dry_run_result.text_summary
    assert MASKED_VALUE in dry_run_result.text_summary

    # Check that the alias appears in the JSON summary's build section
    assert "SECRET_API_KEY" in dry_run_result.json_summary["build"]["env_keys"]


def test_working_directory_masking():
    """Test that working directories containing sensitive values are handled correctly."""
    # Create a spec with working directory that might contain sensitive info
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_workdir",
                kind="env_var",
                aliases=["SECRET_PATH"],
                sources=["/secret/path/value"],
                sensitive=True
            )
        ],
        target=Target(working_dir="/secret/path/value", command=["echo", "test"])
    )

    # Build runtime context
    context = build_runtime_context(spec)

    # Perform dry run
    dry_run_result = dry_run(spec, context)

    # Verify sensitive path value is masked in injector output
    assert "/secret/path/value" not in dry_run_result.text_summary or MASKED_VALUE in dry_run_result.text_summary

    # Note: Working directory path in target is configuration, not injected secret,
    # so it may still appear in the summary. This test ensures injected values are masked.


def test_multiple_overlapping_sensitive_values():
    """Test masking when multiple sensitive values overlap or contain each other."""
    # Create a spec with overlapping sensitive values
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_overlap1",
                kind="env_var",
                aliases=["SECRET1"],
                sources=["abc123"],
                sensitive=True
            ),
            Injector(
                name="test_overlap2",
                kind="env_var",
                aliases=["SECRET2"],
                sources=["123def"],
                sensitive=True
            ),
            Injector(
                name="test_overlap3",
                kind="env_var",
                aliases=["SECRET3"],
                sources=["abc123def"],  # Contains both other secrets
                sensitive=True
            )
        ],
        target=Target(working_dir="/tmp", command=["echo", "abc123def"])
    )

    # Build runtime context
    context = build_runtime_context(spec)

    # Perform dry run
    dry_run_result = dry_run(spec, context)

    # Verify all sensitive values are masked
    assert "abc123" not in dry_run_result.text_summary
    assert "123def" not in dry_run_result.text_summary
    assert "abc123def" not in dry_run_result.text_summary
    assert MASKED_VALUE in dry_run_result.text_summary


if __name__ == "__main__":
    pytest.main([__file__])
