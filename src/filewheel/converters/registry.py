"""Available local engines are the only source of real conversion capabilities."""

from collections.abc import Iterable
from pathlib import PurePath

from filewheel.converters.base import Capability, ConversionError, Engine

CATEGORIES = ("Image", "Document", "Markdown/Text", "Audio", "Video")


class Registry:
    def __init__(self, engines: Iterable[Engine]):
        self.engines = {}
        capabilities = []
        for engine in engines:
            if engine.engine_id in self.engines:
                raise ValueError("Duplicate conversion engine")
            if not engine.available():
                continue
            self.engines[engine.engine_id] = engine
            for capability in engine.capabilities:
                if capability.engine_id != engine.engine_id:
                    raise ValueError("Capability engine mismatch")
                if capability.category not in CATEGORIES:
                    raise ValueError("Unknown conversion category")
                capabilities.append(capability)
        keys = [(c.input_extension.lower(), c.output_extension.lower()) for c in capabilities]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate conversion pair")
        self.capabilities = tuple(capabilities)

    def categories(self, path: PurePath) -> tuple[str, ...]:
        return tuple(category for category in CATEGORIES if self.formats(path, category))

    def formats(self, path: PurePath, category: str) -> tuple[Capability, ...]:
        return tuple(c for c in self.capabilities
                     if c.input_extension.lower() == path.suffix.lower() and c.category == category)

    def find(self, source_extension: str, output_extension: str) -> Capability:
        for capability in self.capabilities:
            if (capability.input_extension.lower() == source_extension.lower()
                    and capability.output_extension.lower() == output_extension.lower()):
                return capability
        raise ConversionError("This conversion engine is unavailable or unsupported")


def default_registry() -> Registry:
    from filewheel.converters.images import PillowEngine
    from filewheel.converters.markdown import MarkItDownEngine
    from filewheel.converters.pdf_docx import PdfDocxEngine

    return Registry((PillowEngine(), PdfDocxEngine(), MarkItDownEngine()))
