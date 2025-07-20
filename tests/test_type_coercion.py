"""Tests for type coercion functionality in injectors."""

import os
import tempfile
from pathlib import Path

import pytest

from config_injector.models import Spec, Provider, Injector, Target
from config_injector.core import build_runtime_context
from config_injector.injectors import resolve_injector, _coerce_type
from config_injector.token_engine import TokenEngine
from config_injector.providers import load_providers


class TestTypeCoercion:
    """Tests for the _coerce_type function."""

    def test_string_type_coercion(self):
        """Test string type coercion."""
        value, errors = _coerce_type("hello", "string")
        assert value == "hello"
        assert errors == []

    def test_int_type_coercion_valid(self):
        """Test valid integer type coercion."""
        value, errors = _coerce_type("42", "int")
        assert value == "42"
        assert errors == []

    def test_int_type_coercion_invalid(self):
        """Test invalid integer type coercion."""
        value, errors = _coerce_type("not_a_number", "int")
        assert value is None
        assert len(errors) == 1
        assert "Type coercion failed" in errors[0]

    def test_bool_type_coercion_true_values(self):
        """Test boolean type coercion for true values."""
        true_values = ["true", "1", "yes", "on", "TRUE", "Yes", "ON"]
        for val in true_values:
            value, errors = _coerce_type(val, "bool")
            assert value == "true", f"Failed for value: {val}"
            assert errors == []

    def test_bool_type_coercion_false_values(self):
        """Test boolean type coercion for false values."""
        false_values = ["false", "0", "no", "off", "FALSE", "No", "OFF"]
        for val in false_values:
            value, errors = _coerce_type(val, "bool")
            assert value == "false", f"Failed for value: {val}"
            assert errors == []

    def test_bool_type_coercion_invalid(self):
        """Test invalid boolean type coercion."""
        value, errors = _coerce_type("maybe", "bool")
        assert value is None
        assert len(errors) == 1
        assert "Invalid boolean value: maybe" in errors[0]

    def test_list_type_coercion(self):
        """Test list type coercion with default comma delimiter."""
        value, errors = _coerce_type("item1,item2,item3", "list")
        assert value == '["item1", "item2", "item3"]'
        assert errors == []

    def test_list_type_coercion_with_spaces(self):
        """Test list type coercion with spaces and default comma delimiter."""
        value, errors = _coerce_type("item1, item2 , item3", "list")
        assert value == '["item1", "item2", "item3"]'
        assert errors == []

    def test_list_type_coercion_with_custom_delimiter(self):
        """Test list type coercion with custom delimiter."""
        # Create a mock injector with custom delimiter
        injector = Injector(
            name="test_list",
            kind="env_var",
            aliases=["TEST_LIST"],
            sources=["item1|item2|item3"],
            type="list",
            delimiter="|"
        )

        value, errors = _coerce_type("item1|item2|item3", "list", injector)
        assert value == '["item1", "item2", "item3"]'
        assert errors == []

    def test_list_type_coercion_with_semicolon_delimiter(self):
        """Test list type coercion with semicolon delimiter."""
        # Create a mock injector with semicolon delimiter
        injector = Injector(
            name="test_list",
            kind="env_var",
            aliases=["TEST_LIST"],
            sources=["item1;item2;item3"],
            type="list",
            delimiter=";"
        )

        value, errors = _coerce_type("item1;item2;item3", "list", injector)
        assert value == '["item1", "item2", "item3"]'
        assert errors == []

    def test_list_type_coercion_with_space_delimiter(self):
        """Test list type coercion with space delimiter."""
        # Create a mock injector with space delimiter
        injector = Injector(
            name="test_list",
            kind="env_var",
            aliases=["TEST_LIST"],
            sources=["item1 item2 item3"],
            type="list",
            delimiter=" "
        )

        value, errors = _coerce_type("item1 item2 item3", "list", injector)
        assert value == '["item1", "item2", "item3"]'
        assert errors == []

    def test_list_type_coercion_with_colon_delimiter(self):
        """Test list type coercion with colon delimiter."""
        # Create a mock injector with colon delimiter
        injector = Injector(
            name="test_list",
            kind="env_var",
            aliases=["TEST_LIST"],
            sources=["item1:item2:item3"],
            type="list",
            delimiter=":"
        )

        value, errors = _coerce_type("item1:item2:item3", "list", injector)
        assert value == '["item1", "item2", "item3"]'
        assert errors == []

    def test_list_type_coercion_with_custom_delimiter_and_spaces(self):
        """Test list type coercion with custom delimiter and spaces."""
        # Create a mock injector with pipe delimiter
        injector = Injector(
            name="test_list",
            kind="env_var",
            aliases=["TEST_LIST"],
            sources=["item1 | item2 | item3"],
            type="list",
            delimiter="|"
        )

        value, errors = _coerce_type("item1 | item2 | item3", "list", injector)
        assert value == '["item1", "item2", "item3"]'  # Should strip spaces
        assert errors == []

    def test_json_type_coercion_valid(self):
        """Test valid JSON type coercion."""
        json_str = '{"key": "value"}'
        value, errors = _coerce_type(json_str, "json")
        assert value == json_str
        assert errors == []

    def test_json_type_coercion_invalid(self):
        """Test invalid JSON type coercion."""
        value, errors = _coerce_type("{invalid json", "json")
        assert value is None
        assert len(errors) == 1
        assert "Type coercion failed" in errors[0]

    def test_unknown_type_coercion(self):
        """Test unknown type coercion."""
        value, errors = _coerce_type("value", "unknown_type")
        assert value is None
        assert len(errors) == 1
        assert "Unknown type: unknown_type" in errors[0]


class TestPathTypeCoercion:
    """Tests for path type coercion with existence validation."""

    def test_path_type_coercion_existing_file(self):
        """Test path type coercion with existing file."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(b"test content")

        try:
            value, errors = _coerce_type(temp_path, "path")
            assert errors == []
            assert value is not None
            # Should return absolute path
            assert Path(value).is_absolute()
            assert Path(value).exists()
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_path_type_coercion_existing_directory(self):
        """Test path type coercion with existing directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            value, errors = _coerce_type(temp_dir, "path")
            assert errors == []
            assert value is not None
            # Should return absolute path
            assert Path(value).is_absolute()
            assert Path(value).exists()
            assert Path(value).is_dir()

    def test_path_type_coercion_nonexistent_path(self):
        """Test path type coercion with non-existent path."""
        nonexistent_path = "/this/path/does/not/exist"
        value, errors = _coerce_type(nonexistent_path, "path")
        assert value is None
        assert len(errors) == 1
        assert f"Path does not exist: {nonexistent_path}" in errors[0]

    def test_path_type_coercion_relative_path(self):
        """Test path type coercion with relative path."""
        # Create a temporary file in current directory
        temp_filename = "test_temp_file.txt"
        temp_path = Path(temp_filename)
        temp_path.write_text("test content")

        try:
            value, errors = _coerce_type(temp_filename, "path")
            assert errors == []
            assert value is not None
            # Should return absolute path
            assert Path(value).is_absolute()
            assert Path(value).exists()
        finally:
            temp_path.unlink(missing_ok=True)

    def test_path_type_coercion_home_directory(self):
        """Test path type coercion with home directory."""
        home_path = str(Path.home())
        value, errors = _coerce_type(home_path, "path")
        assert errors == []
        assert value is not None
        assert Path(value).is_absolute()
        assert Path(value).exists()
        assert Path(value).is_dir()


class TestPathTypeCoercionIntegration:
    """Integration tests for path type coercion in injectors."""

    def test_injector_with_path_type_existing_file(self):
        """Test injector with path type and existing file."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(b"test content")

        try:
            spec = Spec(
                version="0.1",
                configuration_providers=[],
                configuration_injectors=[
                    Injector(
                        name="config_path",
                        kind="env_var",
                        aliases=["CONFIG_PATH"],
                        sources=[temp_path],
                        type="path"
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

            # Verify
            assert resolved.value is not None
            assert resolved.errors == []
            assert Path(resolved.value).is_absolute()
            assert Path(resolved.value).exists()
            assert "CONFIG_PATH" in resolved.env_updates
            assert resolved.env_updates["CONFIG_PATH"] == resolved.value

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_injector_with_path_type_nonexistent_file(self):
        """Test injector with path type and non-existent file."""
        nonexistent_path = "/this/path/does/not/exist"

        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="config_path",
                    kind="env_var",
                    aliases=["CONFIG_PATH"],
                    sources=[nonexistent_path],
                    type="path"
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

        # Verify
        assert resolved.value is None
        assert len(resolved.errors) == 1
        assert f"Path does not exist: {nonexistent_path}" in resolved.errors[0]
        assert resolved.env_updates == {}

    def test_injector_with_path_type_file_injection(self):
        """Test file injector with path type validation."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(b"test content")

        try:
            spec = Spec(
                version="0.1",
                configuration_providers=[],
                configuration_injectors=[
                    Injector(
                        name="config_file",
                        kind="file",
                        aliases=["--config"],
                        sources=[temp_path],
                        type="path",
                        connector="="
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
            resolved = resolve_injector(spec.configuration_injectors[0], context, providers, token_engine, spec)

            # Verify
            assert resolved.value is not None
            assert resolved.errors == []
            assert Path(resolved.value).is_absolute()
            assert Path(resolved.value).exists()
            assert len(resolved.argv_segments) == 1
            assert resolved.argv_segments[0].startswith("--config=")
            assert len(resolved.files_created) == 1

            # Clean up created files
            for file_path in resolved.files_created:
                file_path.unlink(missing_ok=True)

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_injector_with_path_type_named_injection(self):
        """Test named injector with path type validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            spec = Spec(
                version="0.1",
                configuration_providers=[],
                configuration_injectors=[
                    Injector(
                        name="work_dir",
                        kind="named",
                        aliases=["--workdir"],
                        sources=[temp_dir],
                        type="path",
                        connector="="
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

            # Verify
            assert resolved.value is not None
            assert resolved.errors == []
            assert Path(resolved.value).is_absolute()
            assert Path(resolved.value).exists()
            assert Path(resolved.value).is_dir()
            assert len(resolved.argv_segments) == 1
            assert resolved.argv_segments[0].startswith("--workdir=")


class TestListDelimiterIntegration:
    """Integration tests for configurable list delimiter in injectors."""

    def test_injector_with_custom_delimiter_env_var(self):
        """Test env_var injector with custom delimiter for list type."""
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="tags",
                    kind="env_var",
                    aliases=["TAGS"],
                    sources=["tag1|tag2|tag3"],
                    type="list",
                    delimiter="|"
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

        # Verify
        assert resolved.value == '["tag1", "tag2", "tag3"]'
        assert resolved.errors == []
        assert "TAGS" in resolved.env_updates
        assert resolved.env_updates["TAGS"] == '["tag1", "tag2", "tag3"]'

    def test_injector_with_semicolon_delimiter_named(self):
        """Test named injector with semicolon delimiter for list type."""
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="files",
                    kind="named",
                    aliases=["--files"],
                    sources=["file1.txt;file2.txt;file3.txt"],
                    type="list",
                    delimiter=";",
                    connector="="
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

        # Verify
        assert resolved.value == '["file1.txt", "file2.txt", "file3.txt"]'
        assert resolved.errors == []
        assert len(resolved.argv_segments) == 1
        assert resolved.argv_segments[0] == '--files=["file1.txt", "file2.txt", "file3.txt"]'

    def test_injector_with_space_delimiter_positional(self):
        """Test positional injector with space delimiter for list type."""
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="args",
                    kind="positional",
                    sources=["arg1 arg2 arg3"],
                    type="list",
                    delimiter=" "
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

        # Verify
        assert resolved.value == '["arg1", "arg2", "arg3"]'
        assert resolved.errors == []
        assert len(resolved.argv_segments) == 1
        assert resolved.argv_segments[0] == '["arg1", "arg2", "arg3"]'

    def test_injector_with_colon_delimiter_file(self):
        """Test file injector with colon delimiter for list type."""
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="paths",
                    kind="file",
                    aliases=["--config"],
                    sources=["path1:path2:path3"],
                    type="list",
                    delimiter=":",
                    connector="="
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
        resolved = resolve_injector(spec.configuration_injectors[0], context, providers, token_engine, spec)

        # Verify
        assert resolved.value == '["path1", "path2", "path3"]'
        assert resolved.errors == []
        assert len(resolved.argv_segments) == 1
        assert resolved.argv_segments[0].startswith("--config=")
        assert len(resolved.files_created) == 1

        # Clean up created files
        for file_path in resolved.files_created:
            file_path.unlink(missing_ok=True)

    def test_injector_with_default_comma_delimiter(self):
        """Test injector with default comma delimiter (backward compatibility)."""
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="items",
                    kind="env_var",
                    aliases=["ITEMS"],
                    sources=["item1,item2,item3"],
                    type="list"
                    # No delimiter specified, should default to comma
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

        # Verify
        assert resolved.value == '["item1", "item2", "item3"]'
        assert resolved.errors == []
        assert "ITEMS" in resolved.env_updates
        assert resolved.env_updates["ITEMS"] == '["item1", "item2", "item3"]'

    def test_injector_with_complex_delimiter_and_spaces(self):
        """Test injector with complex delimiter and spaces."""
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[
                Injector(
                    name="complex_list",
                    kind="env_var",
                    aliases=["COMPLEX_LIST"],
                    sources=["item with spaces :: another item :: third item"],
                    type="list",
                    delimiter=" :: "
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

        # Verify
        assert resolved.value == '["item with spaces", "another item", "third item"]'
        assert resolved.errors == []
        assert "COMPLEX_LIST" in resolved.env_updates
        assert resolved.env_updates["COMPLEX_LIST"] == '["item with spaces", "another item", "third item"]'


if __name__ == "__main__":
    pytest.main([__file__])
