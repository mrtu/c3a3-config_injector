"""Tests for the sequence counter functionality."""

import os
import tempfile
from pathlib import Path

import pytest

from config_injector.models import Spec, Target, Stream
from config_injector.core import build_runtime_context, dry_run, execute
from config_injector.streams import StreamWriter, prepare_stream
from config_injector.token_engine import TokenEngine


def test_sequence_counter_increment():
    """Test that the sequence counter is incremented correctly."""
    # Create a minimal spec
    spec = Spec(
        version="0.1",
        configuration_providers=[],
        configuration_injectors=[],
        target=Target(working_dir="/tmp", command=["echo", "test"])
    )
    
    # Build runtime context
    context = build_runtime_context(spec)
    
    # Initial sequence should be 1
    assert context.seq == 1
    
    # Run dry_run, which should increment the sequence
    report = dry_run(spec, context)
    
    # Sequence should now be 2
    assert context.seq == 2
    
    # Create a StreamWriter
    writer = StreamWriter()
    
    # Run execute, which should increment the sequence if context is provided
    execute(spec, report.build, writer, context=context)
    
    # Sequence should now be 3
    assert context.seq == 3


def test_sequence_counter_in_path():
    """Test that the sequence counter is used correctly in file paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a spec with a stream that uses the SEQ token
        spec = Spec(
            version="0.1",
            configuration_providers=[],
            configuration_injectors=[],
            target=Target(
                working_dir="/tmp",
                command=["echo", "test"],
                stdout=Stream(
                    path=f"{tmpdir}/test-${{SEQ}}.log",
                    tee_terminal=False,
                    append=False,
                    format="text"
                )
            )
        )
        
        # Build runtime context
        context = build_runtime_context(spec)
        
        # Create token engine
        token_engine = TokenEngine(context)
        
        # Prepare the stream
        config = prepare_stream(spec.target.stdout, context, token_engine)
        
        # Check that the path has the expected format
        assert str(config.path) == f"{tmpdir}/test-0001.log"
        
        # Increment sequence
        context.seq += 1
        
        # Prepare the stream again
        config = prepare_stream(spec.target.stdout, context, token_engine)
        
        # Check that the path has the expected format with incremented sequence
        assert str(config.path) == f"{tmpdir}/test-0002.log"


def test_collision_safe_naming_patterns():
    """Test various collision-safe naming patterns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a runtime context
        context = build_runtime_context(
            Spec(
                version="0.1",
                configuration_providers=[],
                configuration_injectors=[],
                target=Target(working_dir="/tmp", command=["echo", "test"])
            )
        )
        
        # Create token engine
        token_engine = TokenEngine(context)
        
        # Test PID pattern
        stream = Stream(path=f"{tmpdir}/app-${{PID}}.log")
        config = prepare_stream(stream, context, token_engine)
        assert str(config.path) == f"{tmpdir}/app-{context.pid}.log"
        
        # Test SEQ pattern
        stream = Stream(path=f"{tmpdir}/app-${{SEQ}}.log")
        config = prepare_stream(stream, context, token_engine)
        assert str(config.path) == f"{tmpdir}/app-0001.log"
        
        # Test DATE/TIME pattern
        stream = Stream(path=f"{tmpdir}/app-${{DATE:%Y%m%d}}-${{TIME:%H%M%S}}.log")
        config = prepare_stream(stream, context, token_engine)
        date_str = context.now.strftime("%Y%m%d")
        time_str = context.now.strftime("%H%M%S")
        assert str(config.path) == f"{tmpdir}/app-{date_str}-{time_str}.log"
        
        # Test UUID pattern
        stream = Stream(path=f"{tmpdir}/app-${{UUID}}.log")
        config = prepare_stream(stream, context, token_engine)
        path_str = str(config.path)
        assert path_str.startswith(f"{tmpdir}/app-")
        assert path_str.endswith(".log")
        uuid_part = path_str[len(f"{tmpdir}/app-"):-4]
        assert len(uuid_part) == 36  # Standard UUID length
        
        # Test combined pattern
        stream = Stream(path=f"{tmpdir}/app-${{PID}}-${{SEQ}}.log")
        config = prepare_stream(stream, context, token_engine)
        assert str(config.path) == f"{tmpdir}/app-{context.pid}-0001.log"


if __name__ == "__main__":
    pytest.main([__file__])