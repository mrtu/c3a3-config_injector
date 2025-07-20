"""Configuration Wrapping Framework - Declarative YAML specs for wrapping executables."""

__version__ = "0.1.0"

from .models import Spec, Provider, Injector, Target, Stream
from .core import load_spec, dry_run, execute

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