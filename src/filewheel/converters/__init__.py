"""Local conversion engines, independently usable without Qt or Windows APIs."""

from filewheel.converters.base import (
    Capability,
    ConversionCancelled,
    ConversionError,
    ConversionResult,
    EngineOutput,
)
from filewheel.converters.manager import ConversionManager
from filewheel.converters.registry import Registry, default_registry

__all__ = [
    "Capability",
    "ConversionCancelled",
    "ConversionError",
    "ConversionManager",
    "ConversionResult",
    "EngineOutput",
    "Registry",
    "default_registry",
]
