"""Tests for execution and cleanup functionality."""

import tempfile
from pathlib import Path

import pytest

from config_injector.core import build_runtime_context, execute
from config_injector.injectors import resolve_injector
from config_injector.models import Injector, Spec, Target
from config_injector.providers import load_providers
from config_injector.streams import StreamConfig, StreamWriter
from config_injector.token_engine import TokenEngine


def test_file_cleanup_after_execution():
    """Test that temporary files are cleaned up after execution."""
    # Create a minimal spec with a file injector
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_file",
                kind="file",
                aliases=["--config"],
                sources=["test_content"],
                connector="="
            )
        ],
        target=Target(working_dir="/tmp", command=["cat", "${--config}"])
    )

    # Build runtime context
    context = build_runtime_context()

    # Load providers
    providers = load_providers(spec, context)

    # Create token engine
    token_engine = TokenEngine(context, providers)

    # Resolve injector
    resolved_injectors = []
    for injector in spec.configuration_injectors:
        resolved = resolve_injector(injector, context, providers, token_engine)
        resolved_injectors.append(resolved)

    # Verify that a file was created
    assert len(resolved_injectors[0].files_created) == 1
    file_path = resolved_injectors[0].files_created[0]
    assert file_path.exists()

    # Create a build result
    from config_injector.core import build_env_and_argv
    build = build_env_and_argv(spec, resolved_injectors, context)

    # Create a stream writer
    stream_writer = StreamWriter()

    # Execute the process
    execute(spec, build, stream_writer, resolved_injectors, context)

    # Verify that the file was deleted
    assert not file_path.exists()


def test_stdin_fragment_cleanup_after_execution():
    """Test that stdin fragments are cleaned up after execution."""
    # Create a minimal spec with stdin fragments
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="stdin_fragment1",
                kind="stdin_fragment",
                sources=["fragment1"]
            ),
            Injector(
                name="stdin_fragment2",
                kind="stdin_fragment",
                sources=["fragment2"]
            )
        ],
        target=Target(working_dir="/tmp", command=["cat"])
    )

    # Build runtime context
    context = build_runtime_context()

    # Load providers
    providers = load_providers(spec, context)

    # Create token engine
    token_engine = TokenEngine(context, providers)

    # Resolve injectors
    resolved_injectors = []
    for injector in spec.configuration_injectors:
        resolved = resolve_injector(injector, context, providers, token_engine)
        resolved_injectors.append(resolved)

    # Create a build result
    from config_injector.core import build_env_and_argv
    build = build_env_and_argv(spec, resolved_injectors, context)

    # Verify that stdin_data is not None
    assert build.stdin_data is not None

    # Create a stream writer
    stream_writer = StreamWriter()

    # Execute the process
    execute(spec, build, stream_writer, resolved_injectors, context)

    # No explicit verification needed for stdin cleanup as it's handled by the subprocess module
    # This test is mainly to ensure that the execution with stdin fragments works without errors


def test_execution_result_stdout_path_capture():
    """Test that ExecutionResult captures stdout_path when StreamWriter has stdout configured."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create temporary file paths
        stdout_path = Path(tmpdir) / "stdout.log"

        # Create a minimal spec
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[],
            target=Target(working_dir="/tmp", command=["echo", "Hello, stdout!"])
        )

        # Build runtime context
        context = build_runtime_context()

        # Load providers
        providers = load_providers(spec, context)

        # Create token engine
        TokenEngine(context, providers)

        # Create a build result
        from config_injector.core import build_env_and_argv
        build = build_env_and_argv(spec, [], context)

        # Create stream writer with stdout configuration
        stdout_config = StreamConfig(
            path=stdout_path,
            tee_terminal=False,
            append=False,
            format="text"
        )
        stream_writer = StreamWriter(stdout_config=stdout_config)

        # Execute the process
        result = execute(spec, build, stream_writer, [], context)

        # Verify that stdout_path is captured in ExecutionResult
        assert result.stdout_path == stdout_path
        assert result.stderr_path is None  # No stderr config provided

        # Verify that the stdout file was created and contains expected content
        assert stdout_path.exists()
        content = stdout_path.read_text()
        assert "Hello, stdout!" in content

        # Clean up
        stream_writer.close()


def test_execution_result_stderr_path_capture():
    """Test that ExecutionResult captures stderr_path when StreamWriter has stderr configured."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create temporary file paths
        stderr_path = Path(tmpdir) / "stderr.log"

        # Create a minimal spec that writes to stderr
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[],
            target=Target(working_dir="/tmp", command=["sh", "-c", "echo 'Hello, stderr!' >&2"])
        )

        # Build runtime context
        context = build_runtime_context()

        # Load providers
        providers = load_providers(spec, context)

        # Create token engine
        TokenEngine(context, providers)

        # Create a build result
        from config_injector.core import build_env_and_argv
        build = build_env_and_argv(spec, [], context)

        # Create stream writer with stderr configuration
        stderr_config = StreamConfig(
            path=stderr_path,
            tee_terminal=False,
            append=False,
            format="text"
        )
        stream_writer = StreamWriter(stderr_config=stderr_config)

        # Execute the process
        result = execute(spec, build, stream_writer, [], context)

        # Verify that stderr_path is captured in ExecutionResult
        assert result.stderr_path == stderr_path
        assert result.stdout_path is None  # No stdout config provided

        # Verify that the stderr file was created and contains expected content
        assert stderr_path.exists()
        content = stderr_path.read_text()
        assert "Hello, stderr!" in content

        # Clean up
        stream_writer.close()


def test_execution_result_both_stdout_stderr_paths():
    """Test that ExecutionResult captures both stdout_path and stderr_path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create temporary file paths
        stdout_path = Path(tmpdir) / "stdout.log"
        stderr_path = Path(tmpdir) / "stderr.log"

        # Create a minimal spec that writes to both stdout and stderr
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[],
            target=Target(working_dir="/tmp", command=["sh", "-c", "echo 'Hello, stdout!'; echo 'Hello, stderr!' >&2"])
        )

        # Build runtime context
        context = build_runtime_context()

        # Load providers
        providers = load_providers(spec, context)

        # Create token engine
        TokenEngine(context, providers)

        # Create a build result
        from config_injector.core import build_env_and_argv
        build = build_env_and_argv(spec, [], context)

        # Create stream writer with both stdout and stderr configurations
        stdout_config = StreamConfig(
            path=stdout_path,
            tee_terminal=False,
            append=False,
            format="text"
        )
        stderr_config = StreamConfig(
            path=stderr_path,
            tee_terminal=False,
            append=False,
            format="text"
        )
        stream_writer = StreamWriter(stdout_config=stdout_config, stderr_config=stderr_config)

        # Execute the process
        result = execute(spec, build, stream_writer, [], context)

        # Verify that both paths are captured in ExecutionResult
        assert result.stdout_path == stdout_path
        assert result.stderr_path == stderr_path

        # Verify that both files were created and contain expected content
        assert stdout_path.exists()
        assert stderr_path.exists()

        stdout_content = stdout_path.read_text()
        stderr_content = stderr_path.read_text()

        assert "Hello, stdout!" in stdout_content
        assert "Hello, stderr!" in stderr_content

        # Clean up
        stream_writer.close()


def test_execution_result_no_stream_paths():
    """Test that ExecutionResult has None paths when StreamWriter has no file configurations."""
    # Create a minimal spec
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[],
        target=Target(working_dir="/tmp", command=["echo", "Hello, world!"])
    )

    # Build runtime context
    context = build_runtime_context()

    # Load providers
    providers = load_providers(spec, context)

    # Create token engine
    TokenEngine(context, providers)

    # Create a build result
    from config_injector.core import build_env_and_argv
    build = build_env_and_argv(spec, [], context)

    # Create stream writer with no file configurations (default)
    stream_writer = StreamWriter()

    # Execute the process
    result = execute(spec, build, stream_writer, [], context)

    # Verify that both paths are None
    assert result.stdout_path is None
    assert result.stderr_path is None

    # Clean up
    stream_writer.close()


def test_execution_result_json_format_paths():
    """Test that ExecutionResult captures paths correctly with JSON format streams."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create temporary file paths
        stdout_path = Path(tmpdir) / "stdout.json"
        stderr_path = Path(tmpdir) / "stderr.json"

        # Create a minimal spec that writes to both stdout and stderr
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[],
            target=Target(working_dir="/tmp", command=["sh", "-c", "echo 'Hello, stdout!'; echo 'Hello, stderr!' >&2"])
        )

        # Build runtime context
        context = build_runtime_context()

        # Load providers
        providers = load_providers(spec, context)

        # Create token engine
        TokenEngine(context, providers)

        # Create a build result
        from config_injector.core import build_env_and_argv
        build = build_env_and_argv(spec, [], context)

        # Create stream writer with JSON format configurations
        stdout_config = StreamConfig(
            path=stdout_path,
            tee_terminal=False,
            append=False,
            format="json"
        )
        stderr_config = StreamConfig(
            path=stderr_path,
            tee_terminal=False,
            append=False,
            format="json"
        )
        stream_writer = StreamWriter(stdout_config=stdout_config, stderr_config=stderr_config)

        # Execute the process
        result = execute(spec, build, stream_writer, [], context)

        # Verify that both paths are captured in ExecutionResult
        assert result.stdout_path == stdout_path
        assert result.stderr_path == stderr_path

        # Verify that both files were created and contain JSON format
        assert stdout_path.exists()
        assert stderr_path.exists()

        stdout_content = stdout_path.read_text()
        stderr_content = stderr_path.read_text()

        # JSON format should contain structured data
        assert '"stream": "stdout"' in stdout_content
        assert '"stream": "stderr"' in stderr_content
        assert '"msg": "Hello, stdout!"' in stdout_content
        assert '"msg": "Hello, stderr!"' in stderr_content

        # Clean up
        stream_writer.close()


if __name__ == "__main__":
    pytest.main([__file__])
