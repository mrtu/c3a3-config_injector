"""Integration tests for the Configuration Wrapping Framework.

These tests verify the full pipeline from spec loading to execution,
covering dry-run mode, live run mode, and file/stdin injectors.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from config_injector.core import (
    build_env_and_argv,
    build_runtime_context,
    dry_run,
    execute,
    load_spec,
)
from config_injector.injectors import resolve_injector
from config_injector.models import FilterRule, Injector, Provider, Spec, Target
from config_injector.providers import load_providers
from config_injector.streams import StreamWriter
from config_injector.token_engine import TokenEngine


class TestDryRunIntegration:
    """Integration tests for dry-run mode."""

    def test_dry_run_with_multiple_providers_and_injectors(self):
        """Test dry-run with complex spec including multiple providers and injectors."""
        # Create a temporary dotenv file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("DB_HOST=localhost\n")
            f.write("DB_PORT=5432\n")
            f.write("API_KEY=secret123\n")
            dotenv_path = f.name

        try:
            spec = Spec(
                version="0.1",
                configuration_providers=[
                    Provider(
                        type="env",
                        id="env",
                        name="Environment Variables",
                        passthrough=True,
                        filter_chain=[
                            FilterRule(include="PATH"),
                            FilterRule(include="HOME"),
                        ],
                    ),
                    Provider(
                        type="dotenv", id="dotenv", name="Dotenv File", path=dotenv_path
                    ),
                ],
                configuration_injectors=[
                    Injector(
                        name="database_host",
                        kind="env_var",
                        aliases=["DATABASE_HOST"],
                        sources=["${PROVIDER:dotenv:DB_HOST}"],
                    ),
                    Injector(
                        name="database_port",
                        kind="named",
                        aliases=["--port"],
                        sources=["${PROVIDER:dotenv:DB_PORT}"],
                        type="int",
                    ),
                    Injector(
                        name="config_file",
                        kind="file",
                        aliases=["--config"],
                        sources=[
                            "host=${PROVIDER:dotenv:DB_HOST}\nport=${PROVIDER:dotenv:DB_PORT}"
                        ],
                        connector="=",
                    ),
                    Injector(
                        name="api_key",
                        kind="stdin_fragment",
                        sources=["${PROVIDER:dotenv:API_KEY}"],
                        sensitive=True,
                    ),
                ],
                target=Target(
                    working_dir="/tmp", command=["myapp", "${--port}", "${--config}"]
                ),
            )

            # Build runtime context
            context = build_runtime_context()

            # Perform dry run
            report = dry_run(spec, context)

            # Verify text summary contains expected sections
            assert "Providers Loaded" in report.text_summary
            assert "Injection Plan" in report.text_summary
            assert "Final Invocation" in report.text_summary
            assert "env" in report.text_summary
            assert "dotenv" in report.text_summary

            # Verify JSON summary structure
            assert "spec" in report.json_summary
            assert "providers" in report.json_summary
            assert "injections" in report.json_summary
            assert "build" in report.json_summary

            # Verify providers are loaded
            assert "env" in report.json_summary["providers"]
            assert "dotenv" in report.json_summary["providers"]

            # Verify injections are planned
            assert len(report.json_summary["injections"]) == 4
            injection_names = [inj["name"] for inj in report.json_summary["injections"]]
            assert "database_host" in injection_names
            assert "database_port" in injection_names
            assert "config_file" in injection_names
            assert "api_key" in injection_names

            # Verify sensitive data is masked
            api_key_injection = next(
                inj
                for inj in report.json_summary["injections"]
                if inj["name"] == "api_key"
            )
            assert api_key_injection["sensitive"] is True
            # In dry-run mode, sensitive values might be None or masked
            value_str = str(api_key_injection["value"])
            assert value_str == "None" or "<masked>" in value_str

            # Verify build result
            assert "env_keys" in report.json_summary["build"]
            assert "argv" in report.json_summary["build"]
            assert "DATABASE_HOST" in report.json_summary["build"]["env_keys"]

        finally:
            # Clean up
            Path(dotenv_path).unlink(missing_ok=True)

    def test_dry_run_with_conditional_injection(self):
        """Test dry-run with conditional injection based on when expressions."""
        spec = Spec(
            version="0.1",
            configuration_providers=[
                Provider(
                    type="env", id="env", name="Environment Variables", passthrough=True
                )
            ],
            configuration_injectors=[
                Injector(
                    name="debug_flag",
                    kind="named",
                    aliases=["--debug"],
                    sources=["true"],
                    when="${ENV:DEBUG|false} == 'true'",
                ),
                Injector(
                    name="production_flag",
                    kind="named",
                    aliases=["--production"],
                    sources=["true"],
                    when="${ENV:PRODUCTION|false} == 'true'",
                ),
            ],
            target=Target(working_dir="/tmp", command=["myapp"]),
        )

        # Test with DEBUG=true
        with patch.dict(os.environ, {"DEBUG": "true"}, clear=False):
            context = build_runtime_context()
            report = dry_run(spec, context)

            # Should include debug flag
            injection_names = [inj["name"] for inj in report.json_summary["injections"]]
            assert "debug_flag" in injection_names
            assert "production_flag" not in injection_names

        # Test with PRODUCTION=true
        with patch.dict(
            os.environ, {"PRODUCTION": "true", "DEBUG": "false"}, clear=False
        ):
            context = build_runtime_context()
            report = dry_run(spec, context)

            # Should include production flag
            injection_names = [inj["name"] for inj in report.json_summary["injections"]]
            assert "production_flag" in injection_names
            assert "debug_flag" not in injection_names


class TestLiveRunIntegration:
    """Integration tests for live run mode."""

    def test_live_run_with_env_var_injection(self):
        """Test live run with environment variable injection."""
        spec = Spec(
            version="0.1",
            configuration_providers=[
                Provider(
                    type="env", id="env", name="Environment Variables", passthrough=True
                )
            ],
            configuration_injectors=[
                Injector(
                    name="test_var",
                    kind="env_var",
                    aliases=["TEST_INTEGRATION_VAR"],
                    sources=["integration_test_value"],
                )
            ],
            target=Target(working_dir="/tmp", command=["env"]),
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

        # Build env and argv
        build = build_env_and_argv(spec, resolved_injectors, context)

        # Create stream writer
        stream_writer = StreamWriter()

        # Execute
        result = execute(spec, build, stream_writer, resolved_injectors, context)

        # Verify execution was successful
        assert result.exit_code == 0

    def test_live_run_with_named_and_positional_injection(self):
        """Test live run with named and positional argument injection."""
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="output_format",
                    kind="named",
                    aliases=["--format"],
                    sources=["json"],
                    connector="=",
                ),
                Injector(
                    name="input_file",
                    kind="positional",
                    sources=["/etc/passwd"],
                    position=0,
                ),
            ],
            target=Target(working_dir="/tmp", command=["echo", "Processing"]),
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

        # Build env and argv
        build = build_env_and_argv(spec, resolved_injectors, context)

        # Verify argv construction
        expected_argv = ["echo", "Processing", "--format=json", "/etc/passwd"]
        assert build.argv == expected_argv

        # Create stream writer
        stream_writer = StreamWriter()

        # Execute
        result = execute(spec, build, stream_writer, resolved_injectors, context)

        # Verify execution was successful
        assert result.exit_code == 0


class TestFileInjectorIntegration:
    """Integration tests for file injector."""

    def test_file_injector_dry_run_and_live_run(self):
        """Test file injector in both dry-run and live run modes."""
        config_content = """
database:
  host: localhost
  port: 5432
  name: myapp
logging:
  level: info
  file: /var/log/myapp.log
"""

        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="config_file",
                    kind="file",
                    aliases=["--config"],
                    sources=[config_content.strip()],
                    connector="=",
                )
            ],
            target=Target(working_dir="/tmp", command=["cat", "${--config}"]),
        )

        # Test dry-run mode
        context = build_runtime_context()
        report = dry_run(spec, context)

        # Verify dry-run shows file injection plan
        assert "config_file" in [
            inj["name"] for inj in report.json_summary["injections"]
        ]
        config_injection = next(
            inj
            for inj in report.json_summary["injections"]
            if inj["name"] == "config_file"
        )
        assert config_injection["kind"] == "file"
        assert "database:" in config_injection["value"]

        # Test live run mode
        providers = load_providers(spec, context)
        token_engine = TokenEngine(context, providers)

        resolved_injectors = []
        for injector in spec.configuration_injectors:
            resolved = resolve_injector(
                injector, context, providers, token_engine, spec
            )
            resolved_injectors.append(resolved)

        # Verify file was created
        assert len(resolved_injectors[0].files_created) == 1
        file_path = resolved_injectors[0].files_created[0]
        assert file_path.exists()
        assert config_content.strip() == file_path.read_text().strip()

        # Build and execute
        build = build_env_and_argv(spec, resolved_injectors, context, token_engine)
        stream_writer = StreamWriter()
        result = execute(spec, build, stream_writer, resolved_injectors, context)

        # Verify execution was successful
        assert result.exit_code == 0

        # Verify file was cleaned up after execution
        assert not file_path.exists()

    def test_multiple_file_injectors(self):
        """Test multiple file injectors in a single spec."""
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="config1",
                    kind="file",
                    aliases=["--config1"],
                    sources=["config1_content"],
                    connector="=",
                ),
                Injector(
                    name="config2",
                    kind="file",
                    aliases=["--config2"],
                    sources=["config2_content"],
                    connector="=",
                ),
            ],
            target=Target(
                working_dir="/tmp",
                command=[
                    "sh",
                    "-c",
                    "cat ${--config1} && echo '---' && cat ${--config2}",
                ],
            ),
        )

        # Build runtime context
        context = build_runtime_context()

        # Load providers and resolve injectors
        providers = load_providers(spec, context)
        token_engine = TokenEngine(context, providers)

        resolved_injectors = []
        for injector in spec.configuration_injectors:
            resolved = resolve_injector(
                injector, context, providers, token_engine, spec
            )
            resolved_injectors.append(resolved)

        # Verify both files were created
        assert len(resolved_injectors[0].files_created) == 1
        assert len(resolved_injectors[1].files_created) == 1

        file1_path = resolved_injectors[0].files_created[0]
        file2_path = resolved_injectors[1].files_created[0]

        assert file1_path.exists()
        assert file2_path.exists()
        assert file1_path.read_text().strip() == "config1_content"
        assert file2_path.read_text().strip() == "config2_content"

        # Execute
        build = build_env_and_argv(spec, resolved_injectors, context)
        stream_writer = StreamWriter()
        result = execute(spec, build, stream_writer, resolved_injectors, context)

        # Verify execution was successful
        assert result.exit_code == 0

        # Verify files were cleaned up
        assert not file1_path.exists()
        assert not file2_path.exists()


class TestStdinInjectorIntegration:
    """Integration tests for stdin injector."""

    def test_stdin_fragment_dry_run_and_live_run(self):
        """Test stdin fragment injector in both dry-run and live run modes."""
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="input_data",
                    kind="stdin_fragment",
                    sources=["line1\nline2\nline3"],
                )
            ],
            target=Target(working_dir="/tmp", command=["cat"]),
        )

        # Test dry-run mode
        context = build_runtime_context()
        report = dry_run(spec, context)

        # Verify dry-run shows stdin injection plan
        assert "input_data" in [
            inj["name"] for inj in report.json_summary["injections"]
        ]
        stdin_injection = next(
            inj
            for inj in report.json_summary["injections"]
            if inj["name"] == "input_data"
        )
        assert stdin_injection["kind"] == "stdin_fragment"
        assert "line1" in stdin_injection["value"]

        # Test live run mode
        providers = load_providers(spec, context)
        token_engine = TokenEngine(context, providers)

        resolved_injectors = []
        for injector in spec.configuration_injectors:
            resolved = resolve_injector(injector, context, providers, token_engine)
            resolved_injectors.append(resolved)

        # Build and execute
        build = build_env_and_argv(spec, resolved_injectors, context)

        # Verify stdin data was aggregated
        assert build.stdin_data is not None
        assert b"line1\nline2\nline3" in build.stdin_data

        stream_writer = StreamWriter()
        result = execute(spec, build, stream_writer, resolved_injectors, context)

        # Verify execution was successful
        assert result.exit_code == 0

    def test_multiple_stdin_fragments(self):
        """Test multiple stdin fragment injectors aggregated together."""
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="fragment1", kind="stdin_fragment", sources=["first fragment"]
                ),
                Injector(
                    name="fragment2", kind="stdin_fragment", sources=["second fragment"]
                ),
                Injector(
                    name="fragment3", kind="stdin_fragment", sources=["third fragment"]
                ),
            ],
            target=Target(working_dir="/tmp", command=["cat"]),
        )

        # Build runtime context
        context = build_runtime_context()

        # Load providers and resolve injectors
        providers = load_providers(spec, context)
        token_engine = TokenEngine(context, providers)

        resolved_injectors = []
        for injector in spec.configuration_injectors:
            resolved = resolve_injector(injector, context, providers, token_engine)
            resolved_injectors.append(resolved)

        # Build and execute
        build = build_env_and_argv(spec, resolved_injectors, context)

        # Verify all fragments were aggregated
        assert build.stdin_data is not None
        assert b"first fragment" in build.stdin_data
        assert b"second fragment" in build.stdin_data
        assert b"third fragment" in build.stdin_data

        stream_writer = StreamWriter()
        result = execute(spec, build, stream_writer, resolved_injectors, context)

        # Verify execution was successful
        assert result.exit_code == 0

    def test_stdin_fragment_with_sensitive_data(self):
        """Test stdin fragment with sensitive data masking."""
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="secret_input",
                    kind="stdin_fragment",
                    sources=["password=secret123"],
                    sensitive=True,
                )
            ],
            target=Target(working_dir="/tmp", command=["cat"]),
        )

        # Test dry-run mode with sensitive data
        context = build_runtime_context()
        report = dry_run(spec, context)

        # Verify sensitive data is masked in dry-run
        stdin_injection = next(
            inj
            for inj in report.json_summary["injections"]
            if inj["name"] == "secret_input"
        )
        assert stdin_injection["sensitive"] is True
        assert "<masked>" in str(stdin_injection["value"])
        assert "secret123" not in str(stdin_injection["value"])


class TestComplexIntegrationScenarios:
    """Integration tests for complex scenarios combining multiple features."""

    def test_full_pipeline_with_all_injector_types(self):
        """Test a complex spec with all injector types working together."""
        # Create a temporary dotenv file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("DB_HOST=localhost\n")
            f.write("DB_PORT=5432\n")
            f.write("API_SECRET=secret123\n")
            dotenv_path = f.name

        try:
            spec = Spec(
                version="0.1",
                configuration_providers=[
                    Provider(
                        type="dotenv",
                        id="dotenv",
                        name="Configuration File",
                        path=dotenv_path,
                    )
                ],
                configuration_injectors=[
                    # Environment variable injection
                    Injector(
                        name="db_host",
                        kind="env_var",
                        aliases=["DATABASE_HOST"],
                        sources=["${PROVIDER:dotenv:DB_HOST}"],
                    ),
                    # Named argument injection
                    Injector(
                        name="db_port",
                        kind="named",
                        aliases=["--port"],
                        sources=["${PROVIDER:dotenv:DB_PORT}"],
                        connector="=",
                        type="int",
                    ),
                    # Positional argument injection
                    Injector(
                        name="operation",
                        kind="positional",
                        sources=["migrate"],
                        position=0,
                    ),
                    # File injection
                    Injector(
                        name="config_file",
                        kind="file",
                        aliases=["--config"],
                        sources=[
                            "host=${PROVIDER:dotenv:DB_HOST}\nport=${PROVIDER:dotenv:DB_PORT}"
                        ],
                        connector="=",
                    ),
                    # Stdin fragment injection
                    Injector(
                        name="api_secret",
                        kind="stdin_fragment",
                        sources=["${PROVIDER:dotenv:API_SECRET}"],
                        sensitive=True,
                    ),
                ],
                target=Target(
                    working_dir="/tmp", command=["echo", "Running with args:"]
                ),
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
            assert "api_secret" in injection_names

            # Verify sensitive data is masked
            api_secret_injection = next(
                inj
                for inj in report.json_summary["injections"]
                if inj["name"] == "api_secret"
            )
            assert api_secret_injection["sensitive"] is True
            assert "<masked>" in str(api_secret_injection["value"])

            # Test live run
            providers = load_providers(spec, context)
            token_engine = TokenEngine(context, providers)

            resolved_injectors = []
            for injector in spec.configuration_injectors:
                resolved = resolve_injector(injector, context, providers, token_engine)
                resolved_injectors.append(resolved)

            # Verify file was created
            config_file_injector = next(
                inj for inj in resolved_injectors if inj.name == "config_file"
            )
            assert len(config_file_injector.files_created) == 1
            config_file_path = config_file_injector.files_created[0]
            assert config_file_path.exists()

            # Build and execute
            build = build_env_and_argv(spec, resolved_injectors, context, token_engine)

            # Verify environment variables
            assert "DATABASE_HOST" in build.env
            assert build.env["DATABASE_HOST"] == "localhost"

            # Verify argv construction
            assert "migrate" in build.argv  # positional
            assert any("--port=5432" in arg for arg in build.argv)  # named
            assert any("--config=" in arg for arg in build.argv)  # file

            # Verify stdin data
            assert build.stdin_data is not None
            assert b"secret123" in build.stdin_data

            stream_writer = StreamWriter()
            result = execute(spec, build, stream_writer, resolved_injectors, context)

            # Verify execution was successful
            assert result.exit_code == 0

            # Verify file was cleaned up
            assert not config_file_path.exists()

        finally:
            # Clean up
            Path(dotenv_path).unlink(missing_ok=True)

    def test_spec_loading_from_yaml_file(self):
        """Test loading spec from YAML file and running integration test."""
        spec_content = """
version: "0.1"
configuration_providers:
  - type: env
    id: env
    name: Environment Variables
    passthrough: true
    filter_chain: ["HOME", "USER"]

configuration_injectors:
  - name: user_home
    kind: env_var
    aliases: ["USER_HOME_DIR"]
    sources: ["${HOME}"]

  - name: username
    kind: named
    aliases: ["--user"]
    sources: ["${USER}"]
    connector: "="

target:
  working_dir: "/tmp"
  command: ["echo", "Hello", "${--user}", "from", "${USER_HOME_DIR}"]
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
            assert "user_home" in [
                inj["name"] for inj in report.json_summary["injections"]
            ]
            assert "username" in [
                inj["name"] for inj in report.json_summary["injections"]
            ]

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
            # Clean up
            yaml_path.unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__])
