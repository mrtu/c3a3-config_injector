"""Tests for the Configuration Wrapping Framework injectors."""

import os
import tempfile
from pathlib import Path

import pytest

from config_injector.models import Spec, Provider, Injector, Target, Stream
from config_injector.core import build_runtime_context, dry_run
from config_injector.injectors import resolve_injector
from config_injector.token_engine import TokenEngine
from config_injector.providers import load_providers


def test_env_var_injector():
    """Test env_var injector."""
    # Create a minimal spec
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_env_var",
                kind="env_var",
                aliases=["TEST_VAR"],
                sources=["test_value"]
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
    assert resolved.value == "test_value"
    assert resolved.applied_aliases == ["TEST_VAR"]
    assert resolved.env_updates == {"TEST_VAR": "test_value"}
    assert not resolved.argv_segments
    assert not resolved.files_created
    assert not resolved.skipped
    assert not resolved.errors


def test_named_injector():
    """Test named injector."""
    # Create a minimal spec
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_named",
                kind="named",
                aliases=["--test"],
                sources=["test_value"],
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
    assert resolved.value == "test_value"
    assert not resolved.applied_aliases
    assert resolved.argv_segments == ["--test=test_value"]
    assert not resolved.env_updates
    assert not resolved.files_created
    assert not resolved.skipped
    assert not resolved.errors


def test_positional_injector():
    """Test positional injector."""
    # Create a minimal spec
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="test_positional",
                kind="positional",
                sources=["test_value"]
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
    assert resolved.value == "test_value"
    assert not resolved.applied_aliases
    assert resolved.argv_segments == ["test_value"]
    assert not resolved.env_updates
    assert not resolved.files_created
    assert not resolved.skipped
    assert not resolved.errors


def test_file_injector():
    """Test file injector."""
    # Create a minimal spec
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
    assert resolved.value == "test_content"
    assert not resolved.applied_aliases
    assert len(resolved.argv_segments) == 1
    assert resolved.argv_segments[0].startswith("--config=")
    assert len(resolved.files_created) == 1
    assert not resolved.skipped
    assert not resolved.errors
    
    # Clean up
    for file_path in resolved.files_created:
        file_path.unlink(missing_ok=True)


def test_stdin_fragment_injector():
    """Test stdin_fragment injector."""
    # Create a minimal spec with multiple stdin fragments
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
    context = build_runtime_context(spec)
    
    # Load providers
    providers = load_providers(spec, context)
    
    # Create token engine
    token_engine = TokenEngine(context, providers)
    
    # Resolve injectors
    resolved_injectors = []
    for injector in spec.configuration_injectors:
        resolved = resolve_injector(injector, context, providers, token_engine)
        resolved_injectors.append(resolved)
    
    # Verify individual resolved injectors
    assert resolved_injectors[0].value == "fragment1"
    assert resolved_injectors[1].value == "fragment2"
    
    # Perform dry run to get build result
    dry_run_result = dry_run(spec, context)
    
    # Verify stdin_data in build result
    assert dry_run_result.build.stdin_data is not None
    assert b"fragment1" in dry_run_result.build.stdin_data
    assert b"fragment2" in dry_run_result.build.stdin_data


def test_conditional_stdin_fragment_injector():
    """Test conditional stdin_fragment injector."""
    # Create a minimal spec with conditional stdin fragments
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[
            Injector(
                name="stdin_fragment1",
                kind="stdin_fragment",
                sources=["fragment1"],
                when="true"
            ),
            Injector(
                name="stdin_fragment2",
                kind="stdin_fragment",
                sources=["fragment2"],
                when="false"
            )
        ],
        target=Target(working_dir="/tmp", command=["cat"])
    )
    
    # Build runtime context
    context = build_runtime_context(spec)
    
    # Perform dry run to get build result
    dry_run_result = dry_run(spec, context)
    
    # Verify stdin_data in build result
    assert dry_run_result.build.stdin_data is not None
    assert b"fragment1" in dry_run_result.build.stdin_data
    assert b"fragment2" not in dry_run_result.build.stdin_data


if __name__ == "__main__":
    pytest.main([__file__])