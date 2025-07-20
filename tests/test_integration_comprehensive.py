"""Comprehensive integration tests for the Configuration Wrapping Framework.

This module provides thorough integration testing covering:
- Dry-run functionality with multiple providers and injectors
- Live run execution with various injector types
- File injector creation, usage, and cleanup
- Stdin fragment injection and aggregation
- Complex scenarios combining multiple features
"""

import tempfile
from pathlib import Path

import pytest

from config_injector.core import (
    build_env_and_argv,
    build_runtime_context,
    dry_run,
    execute,
    load_spec,
)
from config_injector.injectors import resolve_injector
from config_injector.models import Injector, Provider, Spec, Target
from config_injector.providers import load_providers
from config_injector.streams import StreamWriter
from config_injector.token_engine import TokenEngine


class TestDryRunComprehensive:
    """Comprehensive tests for dry-run functionality."""

    def test_dry_run_basic_functionality(self):
        """Test basic dry-run functionality with simple injectors."""
        spec = Spec(
            version="0.1",
            configuration_providers=[
                Provider(
                    type="env",
                    id="env",
                    name="Environment Variables",
                    passthrough=True
                )
            ],
            configuration_injectors=[
                Injector(
                    name="test_env",
                    kind="env_var",
                    aliases=["TEST_VAR"],
                    sources=["test_value"]
                ),
                Injector(
                    name="test_named",
                    kind="named",
                    aliases=["--test"],
                    sources=["named_value"],
                    connector="="
                )
            ],
            target=Target(
                working_dir="/tmp",
                command=["echo", "test"]
            )
        )

        context = build_runtime_context()
        report = dry_run(spec, context)

        # Verify report structure
        assert hasattr(report, "providers")
        assert hasattr(report, "resolved")
        assert hasattr(report, "build")
        assert hasattr(report, "text_summary")
        assert hasattr(report, "json_summary")

        # Verify text summary contains expected sections
        assert "Providers Loaded" in report.text_summary
        assert "Injection Plan" in report.text_summary
        assert "Final Invocation" in report.text_summary

        # Verify JSON summary structure
        assert "spec" in report.json_summary
        assert "providers" in report.json_summary
        assert "injections" in report.json_summary
        assert "build" in report.json_summary

        # Verify injections
        assert len(report.json_summary["injections"]) == 2
        injection_names = [inj["name"] for inj in report.json_summary["injections"]]
        assert "test_env" in injection_names
        assert "test_named" in injection_names

        # Verify build result
        assert "env_keys" in report.json_summary["build"]
        assert "argv" in report.json_summary["build"]
        assert isinstance(report.json_summary["build"]["env_keys"], list)
        assert isinstance(report.json_summary["build"]["argv"], list)

    def test_dry_run_with_dotenv_provider(self):
        """Test dry-run with dotenv provider."""
        # Create temporary dotenv file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST_KEY=test_value\n")
            f.write("ANOTHER_KEY=another_value\n")
            dotenv_path = f.name

        try:
            spec = Spec(
                version="0.1",
                configuration_providers=[
                    Provider(
                        type="dotenv",
                        id="dotenv",
                        name="Test Dotenv",
                        path=dotenv_path
                    )
                ],
                configuration_injectors=[
                    Injector(
                        name="test_from_dotenv",
                        kind="env_var",
                        aliases=["INJECTED_VAR"],
                        sources=["${PROVIDER:dotenv:TEST_KEY}"]
                    )
                ],
                target=Target(
                    working_dir="/tmp",
                    command=["echo", "test"]
                )
            )

            context = build_runtime_context()
            report = dry_run(spec, context)

            # Verify provider was loaded
            assert "dotenv" in report.json_summary["providers"]

            # Verify injection was resolved
            injections = report.json_summary["injections"]
            assert len(injections) == 1
            assert injections[0]["name"] == "test_from_dotenv"
            assert injections[0]["resolved"] is True
            assert injections[0]["value"] == "test_value"

        finally:
            Path(dotenv_path).unlink(missing_ok=True)

    def test_dry_run_with_sensitive_data(self):
        """Test dry-run properly masks sensitive data."""
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="secret_data",
                    kind="stdin_fragment",
                    sources=["secret123"],
                    sensitive=True
                ),
                Injector(
                    name="normal_data",
                    kind="env_var",
                    aliases=["NORMAL_VAR"],
                    sources=["normal_value"],
                    sensitive=False
                )
            ],
            target=Target(
                working_dir="/tmp",
                command=["cat"]
            )
        )

        context = build_runtime_context()
        report = dry_run(spec, context)

        # Find the sensitive injection
        secret_injection = next(
            inj for inj in report.json_summary["injections"]
            if inj["name"] == "secret_data"
        )
        normal_injection = next(
            inj for inj in report.json_summary["injections"]
            if inj["name"] == "normal_data"
        )

        # Verify sensitive data is marked as sensitive
        assert secret_injection["sensitive"] is True
        assert normal_injection["sensitive"] is False

        # Verify sensitive data is masked in the value
        assert secret_injection["value"] == "<masked>"
        assert normal_injection["value"] == "normal_value"

        # Verify sensitive data is not in text summary
        assert "secret123" not in report.text_summary
        assert "<masked>" in report.text_summary


class TestLiveRunComprehensive:
    """Comprehensive tests for live run functionality."""

    def test_live_run_env_var_injection(self):
        """Test live run with environment variable injection."""
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="test_var",
                    kind="env_var",
                    aliases=["INJECTED_TEST_VAR"],
                    sources=["test_value_123"]
                )
            ],
            target=Target(
                working_dir="/tmp",
                command=["env"]
            )
        )

        context = build_runtime_context()
        providers = load_providers(spec, context)
        token_engine = TokenEngine(context, providers)

        resolved_injectors = []
        for injector in spec.configuration_injectors:
            resolved = resolve_injector(injector, context, providers, token_engine)
            resolved_injectors.append(resolved)

        build = build_env_and_argv(spec, resolved_injectors, context)

        # Verify environment variable was set
        assert "INJECTED_TEST_VAR" in build.env
        assert build.env["INJECTED_TEST_VAR"] == "test_value_123"

        # Execute and verify success
        stream_writer = StreamWriter()
        result = execute(spec, build, stream_writer, resolved_injectors, context)
        assert result.exit_code == 0

    def test_live_run_named_injection(self):
        """Test live run with named argument injection."""
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="format_arg",
                    kind="named",
                    aliases=["--format"],
                    sources=["json"],
                    connector="="
                )
            ],
            target=Target(
                working_dir="/tmp",
                command=["echo", "test"]
            )
        )

        context = build_runtime_context()
        providers = load_providers(spec, context)
        token_engine = TokenEngine(context, providers)

        resolved_injectors = []
        for injector in spec.configuration_injectors:
            resolved = resolve_injector(injector, context, providers, token_engine)
            resolved_injectors.append(resolved)

        build = build_env_and_argv(spec, resolved_injectors, context)

        # Verify named argument was added
        assert "--format=json" in build.argv

        # Execute and verify success
        stream_writer = StreamWriter()
        result = execute(spec, build, stream_writer, resolved_injectors, context)
        assert result.exit_code == 0

    def test_live_run_positional_injection(self):
        """Test live run with positional argument injection."""
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="input_file",
                    kind="positional",
                    sources=["/etc/hostname"],
                    position=0
                )
            ],
            target=Target(
                working_dir="/tmp",
                command=["cat"]
            )
        )

        context = build_runtime_context()
        providers = load_providers(spec, context)
        token_engine = TokenEngine(context, providers)

        resolved_injectors = []
        for injector in spec.configuration_injectors:
            resolved = resolve_injector(injector, context, providers, token_engine)
            resolved_injectors.append(resolved)

        build = build_env_and_argv(spec, resolved_injectors, context)

        # Verify positional argument was added
        assert "/etc/hostname" in build.argv
        # Should be after the command
        assert build.argv.index("/etc/hostname") > build.argv.index("cat")

        # Execute and verify success
        stream_writer = StreamWriter()
        result = execute(spec, build, stream_writer, resolved_injectors, context)
        assert result.exit_code == 0


class TestFileInjectorComprehensive:
    """Comprehensive tests for file injector functionality."""

    def test_file_injector_dry_run(self):
        """Test file injector in dry-run mode."""
        config_content = "key=value\nother_key=other_value"

        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="config_file",
                    kind="file",
                    aliases=["--config"],
                    sources=[config_content],
                    connector="="
                )
            ],
            target=Target(
                working_dir="/tmp",
                command=["cat", "${--config}"]
            )
        )

        context = build_runtime_context()
        report = dry_run(spec, context)

        # Verify file injection is planned
        injections = report.json_summary["injections"]
        assert len(injections) == 1
        assert injections[0]["name"] == "config_file"
        assert injections[0]["kind"] == "file"
        assert injections[0]["resolved"] is True
        assert config_content in injections[0]["value"]

    def test_file_injector_live_run(self):
        """Test file injector in live run mode."""
        config_content = "test_key=test_value\nother=data"

        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="config_file",
                    kind="file",
                    aliases=["--config"],
                    sources=[config_content],
                    connector="="
                )
            ],
            target=Target(
                working_dir="/tmp",
                command=["echo", "test"]
            )
        )

        context = build_runtime_context()
        providers = load_providers(spec, context)
        token_engine = TokenEngine(context, providers)

        resolved_injectors = []
        for injector in spec.configuration_injectors:
            resolved = resolve_injector(injector, context, providers, token_engine)
            resolved_injectors.append(resolved)

        # Verify file was created
        config_injector = resolved_injectors[0]
        assert len(config_injector.files_created) == 1
        file_path = config_injector.files_created[0]
        assert file_path.exists()
        assert file_path.read_text() == config_content

        # Build and execute
        build = build_env_and_argv(spec, resolved_injectors, context)

        # Verify file path is in argv
        file_arg = f"--config={file_path}"
        assert file_arg in build.argv

        stream_writer = StreamWriter()
        result = execute(spec, build, stream_writer, resolved_injectors, context)

        # Verify execution was successful
        assert result.exit_code == 0

        # Verify file was cleaned up after execution
        assert not file_path.exists()

    def test_multiple_file_injectors(self):
        """Test multiple file injectors working together."""
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="config1",
                    kind="file",
                    aliases=["--config1"],
                    sources=["config1_content"],
                    connector="="
                ),
                Injector(
                    name="config2",
                    kind="file",
                    aliases=["--config2"],
                    sources=["config2_content"],
                    connector="="
                )
            ],
            target=Target(
                working_dir="/tmp",
                command=["echo", "test"]
            )
        )

        context = build_runtime_context()
        providers = load_providers(spec, context)
        token_engine = TokenEngine(context, providers)

        resolved_injectors = []
        for injector in spec.configuration_injectors:
            resolved = resolve_injector(injector, context, providers, token_engine)
            resolved_injectors.append(resolved)

        # Verify both files were created
        file_paths = []
        for resolved_inj in resolved_injectors:
            assert len(resolved_inj.files_created) == 1
            file_path = resolved_inj.files_created[0]
            assert file_path.exists()
            file_paths.append(file_path)

        # Verify file contents
        assert file_paths[0].read_text() == "config1_content"
        assert file_paths[1].read_text() == "config2_content"

        # Build and execute
        build = build_env_and_argv(spec, resolved_injectors, context)
        stream_writer = StreamWriter()
        result = execute(spec, build, stream_writer, resolved_injectors, context)

        # Verify execution was successful
        assert result.exit_code == 0

        # Verify files were cleaned up
        for file_path in file_paths:
            assert not file_path.exists()


class TestStdinInjectorComprehensive:
    """Comprehensive tests for stdin injector functionality."""

    def test_stdin_fragment_dry_run(self):
        """Test stdin fragment injector in dry-run mode."""
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="input_data",
                    kind="stdin_fragment",
                    sources=["line1\nline2\nline3"]
                )
            ],
            target=Target(
                working_dir="/tmp",
                command=["cat"]
            )
        )

        context = build_runtime_context()
        report = dry_run(spec, context)

        # Verify stdin injection is planned
        injections = report.json_summary["injections"]
        assert len(injections) == 1
        assert injections[0]["name"] == "input_data"
        assert injections[0]["kind"] == "stdin_fragment"
        assert injections[0]["resolved"] is True
        assert "line1" in injections[0]["value"]

    def test_stdin_fragment_live_run(self):
        """Test stdin fragment injector in live run mode."""
        test_input = "test line 1\ntest line 2\ntest line 3"

        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="input_data",
                    kind="stdin_fragment",
                    sources=[test_input]
                )
            ],
            target=Target(
                working_dir="/tmp",
                command=["cat"]
            )
        )

        context = build_runtime_context()
        providers = load_providers(spec, context)
        token_engine = TokenEngine(context, providers)

        resolved_injectors = []
        for injector in spec.configuration_injectors:
            resolved = resolve_injector(injector, context, providers, token_engine)
            resolved_injectors.append(resolved)

        build = build_env_and_argv(spec, resolved_injectors, context)

        # Verify stdin data was set
        assert build.stdin_data is not None
        assert test_input.encode("utf-8") == build.stdin_data

        stream_writer = StreamWriter()
        result = execute(spec, build, stream_writer, resolved_injectors, context)

        # Verify execution was successful
        assert result.exit_code == 0

    def test_multiple_stdin_fragments(self):
        """Test multiple stdin fragments are aggregated."""
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="fragment1",
                    kind="stdin_fragment",
                    sources=["first fragment"]
                ),
                Injector(
                    name="fragment2",
                    kind="stdin_fragment",
                    sources=["second fragment"]
                ),
                Injector(
                    name="fragment3",
                    kind="stdin_fragment",
                    sources=["third fragment"]
                )
            ],
            target=Target(
                working_dir="/tmp",
                command=["cat"]
            )
        )

        context = build_runtime_context()
        providers = load_providers(spec, context)
        token_engine = TokenEngine(context, providers)

        resolved_injectors = []
        for injector in spec.configuration_injectors:
            resolved = resolve_injector(injector, context, providers, token_engine)
            resolved_injectors.append(resolved)

        build = build_env_and_argv(spec, resolved_injectors, context)

        # Verify all fragments were aggregated
        assert build.stdin_data is not None
        stdin_str = build.stdin_data.decode("utf-8")
        assert "first fragment" in stdin_str
        assert "second fragment" in stdin_str
        assert "third fragment" in stdin_str

        stream_writer = StreamWriter()
        result = execute(spec, build, stream_writer, resolved_injectors, context)

        # Verify execution was successful
        assert result.exit_code == 0


class TestComplexIntegrationScenarios:
    """Tests for complex scenarios combining multiple features."""

    def test_full_pipeline_all_injector_types(self):
        """Test a complete pipeline with all injector types."""
        # Create temporary dotenv file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("DB_HOST=localhost\n")
            f.write("DB_PORT=5432\n")
            f.write("SECRET_KEY=secret123\n")
            dotenv_path = f.name

        try:
            spec = Spec(
                version="0.1",
                configuration_providers=[
                    Provider(
                        type="dotenv",
                        id="dotenv",
                        name="Configuration",
                        path=dotenv_path
                    )
                ],
                configuration_injectors=[
                    # Environment variable injection
                    Injector(
                        name="db_host",
                        kind="env_var",
                        aliases=["DATABASE_HOST"],
                        sources=["${PROVIDER:dotenv:DB_HOST}"]
                    ),
                    # Named argument injection
                    Injector(
                        name="db_port",
                        kind="named",
                        aliases=["--port"],
                        sources=["${PROVIDER:dotenv:DB_PORT}"],
                        connector="="
                    ),
                    # Positional argument injection
                    Injector(
                        name="operation",
                        kind="positional",
                        sources=["status"],
                        position=0
                    ),
                    # File injection
                    Injector(
                        name="config_file",
                        kind="file",
                        aliases=["--config"],
                        sources=["host=${PROVIDER:dotenv:DB_HOST}\nport=${PROVIDER:dotenv:DB_PORT}"],
                        connector="="
                    ),
                    # Stdin fragment injection (sensitive)
                    Injector(
                        name="secret_input",
                        kind="stdin_fragment",
                        sources=["${PROVIDER:dotenv:SECRET_KEY}"],
                        sensitive=True
                    )
                ],
                target=Target(
                    working_dir="/tmp",
                    command=["echo", "Running command"]
                )
            )

            # Test dry-run first
            context = build_runtime_context()
            report = dry_run(spec, context)

            # Verify all injectors are planned
            injection_names = [inj["name"] for inj in report.json_summary["injections"]]
            assert "db_host" in injection_names
            assert "db_port" in injection_names
            assert "operation" in injection_names
            assert "config_file" in injection_names
            assert "secret_input" in injection_names

            # Verify sensitive data is masked in dry-run
            secret_injection = next(
                inj for inj in report.json_summary["injections"]
                if inj["name"] == "secret_input"
            )
            assert secret_injection["sensitive"] is True
            assert secret_injection["value"] == "<masked>"

            # Test live run
            providers = load_providers(spec, context)
            token_engine = TokenEngine(context, providers)

            resolved_injectors = []
            for injector in spec.configuration_injectors:
                resolved = resolve_injector(injector, context, providers, token_engine)
                resolved_injectors.append(resolved)

            # Verify file was created
            config_injector = next(
                inj for inj in resolved_injectors
                if inj.injector.name == "config_file"
            )
            assert len(config_injector.files_created) == 1
            config_file_path = config_injector.files_created[0]
            assert config_file_path.exists()

            # Build and execute
            build = build_env_and_argv(spec, resolved_injectors, context)

            # Verify environment variables
            assert "DATABASE_HOST" in build.env
            assert build.env["DATABASE_HOST"] == "localhost"

            # Verify argv construction
            assert "status" in build.argv  # positional
            assert "--port=5432" in build.argv  # named
            assert any("--config=" in arg for arg in build.argv)  # file

            # Verify stdin data (should contain actual secret in live run)
            assert build.stdin_data is not None
            assert b"secret123" in build.stdin_data

            stream_writer = StreamWriter()
            result = execute(spec, build, stream_writer, resolved_injectors, context)

            # Verify execution was successful
            assert result.exit_code == 0

            # Verify file was cleaned up
            assert not config_file_path.exists()

        finally:
            Path(dotenv_path).unlink(missing_ok=True)

    def test_yaml_spec_loading_and_execution(self):
        """Test loading spec from YAML and running integration test."""
        spec_content = """
version: "0.1"
configuration_providers:
  - type: env
    id: env
    name: Environment Variables
    passthrough: true

configuration_injectors:
  - name: user_home
    kind: env_var
    aliases: ["USER_HOME_DIR"]
    sources: ["${HOME}"]

  - name: test_flag
    kind: named
    aliases: ["--test"]
    sources: ["enabled"]
    connector: "="

target:
  working_dir: "/tmp"
  command: ["echo", "Hello from", "${USER_HOME_DIR}"]
"""

        # Create temporary YAML file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(spec_content)
            yaml_path = Path(f.name)

        try:
            # Load spec from file
            spec = load_spec(yaml_path)

            # Verify spec was loaded correctly
            assert spec.version == "0.1"
            assert len(spec.configuration_providers) == 1
            assert len(spec.configuration_injectors) == 2
            assert spec.target.working_dir == "/tmp"

            # Test dry-run
            context = build_runtime_context()
            report = dry_run(spec, context)

            # Verify dry-run works with loaded spec
            injection_names = [inj["name"] for inj in report.json_summary["injections"]]
            assert "user_home" in injection_names
            assert "test_flag" in injection_names

            # Test live run
            providers = load_providers(spec, context)
            token_engine = TokenEngine(context, providers)

            resolved_injectors = []
            for injector in spec.configuration_injectors:
                resolved = resolve_injector(injector, context, providers, token_engine)
                resolved_injectors.append(resolved)

            build = build_env_and_argv(spec, resolved_injectors, context)
            stream_writer = StreamWriter()
            result = execute(spec, build, stream_writer, resolved_injectors, context)

            # Verify execution was successful
            assert result.exit_code == 0

        finally:
            yaml_path.unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__])
