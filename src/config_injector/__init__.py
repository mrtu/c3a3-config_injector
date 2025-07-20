"""Configuration Wrapping Framework - Declarative YAML specs for wrapping executables."""

__version__ = "0.1.0"

from .core import dry_run, execute, load_spec
from .models import Injector, Provider, Spec, Stream, Target

__all__ = [
    "Spec",
    "Provider",
    "Injector",
    "Target",
    "Stream",
    "load_spec",
    "dry_run",
    "execute",
]
