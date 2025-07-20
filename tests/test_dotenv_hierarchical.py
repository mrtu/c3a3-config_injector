import os
import tempfile
from pathlib import Path
import shutil

import pytest

from config_injector.models import Provider, Spec, Target
from config_injector.core import build_runtime_context
from config_injector.providers import DotenvProvider

def write_env_file(path: Path, content: str):
    path.write_text(content)


def minimal_spec(working_dir: str) -> Spec:
    return Spec(
        version="0.1",
        env_passthrough=True,
        configuration_providers=[],
        configuration_injectors=[],
        target=Target(working_dir=working_dir, command=["echo", "test"]),
    )


def test_hierarchical_dotenv_deep_first():
    """Test hierarchical dotenv provider with deep-first precedence (closest wins)."""
    with tempfile.TemporaryDirectory() as root_dir:
        root = Path(root_dir)
        # Create directory tree: root/level1/level2
        level1 = root / "level1"
        level2 = level1 / "level2"
        level2.mkdir(parents=True)
        # .env in root
        write_env_file(root / ".env", "FOO=from_root\nBAR=from_root\n")
        # .env in level1
        write_env_file(level1 / ".env", "FOO=from_level1\nBAZ=from_level1\n")
        # .env in level2
        write_env_file(level2 / ".env", "FOO=from_level2\nQUX=from_level2\n")

        provider = Provider(
            type="dotenv",
            id="dotenv_hier",
            name="Hierarchical .env",
            hierarchical=True,
            filename=".env",
            precedence="deep-first",
            filter_chain=[],
        )
        spec = minimal_spec(str(level2))
        context = build_runtime_context(
            spec=spec,
            env=os.environ.copy(),
        )
        # Set working_dir in context.extra
        context.extra["working_dir"] = str(level2)
        dotenv_provider = DotenvProvider(provider)
        merged = dotenv_provider._load_hierarchical(context)
        # Closest wins: FOO from level2, BAR from root, BAZ from level1, QUX from level2
        assert merged["FOO"] == "from_level2"
        assert merged["BAR"] == "from_root"
        assert merged["BAZ"] == "from_level1"
        assert merged["QUX"] == "from_level2"


def test_hierarchical_dotenv_shallow_first():
    """Test hierarchical dotenv provider with shallow-first precedence (root wins)."""
    with tempfile.TemporaryDirectory() as root_dir:
        root = Path(root_dir)
        # Create directory tree: root/level1/level2
        level1 = root / "level1"
        level2 = level1 / "level2"
        level2.mkdir(parents=True)
        # .env in root
        write_env_file(root / ".env", "FOO=from_root\nBAR=from_root\n")
        # .env in level1
        write_env_file(level1 / ".env", "FOO=from_level1\nBAZ=from_level1\n")
        # .env in level2
        write_env_file(level2 / ".env", "FOO=from_level2\nQUX=from_level2\n")

        provider = Provider(
            type="dotenv",
            id="dotenv_hier",
            name="Hierarchical .env",
            hierarchical=True,
            filename=".env",
            precedence="shallow-first",
            filter_chain=[],
        )
        spec = minimal_spec(str(level2))
        context = build_runtime_context(
            spec=spec,
            env=os.environ.copy(),
        )
        # Set working_dir in context.extra
        context.extra["working_dir"] = str(level2)
        dotenv_provider = DotenvProvider(provider)
        merged = dotenv_provider._load_hierarchical(context)
        # Shallowest wins: FOO from root, BAR from root, BAZ from level1, QUX from level2
        assert merged["FOO"] == "from_root"
        assert merged["BAR"] == "from_root"
        assert merged["BAZ"] == "from_level1"
        assert merged["QUX"] == "from_level2" 