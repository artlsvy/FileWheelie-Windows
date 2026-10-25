"""Available local engines are the only source of real conversion capabilities."""

from collections.abc import Iterable
from pathlib import PurePath

from filewheel.converters.base import Capability, ConversionError, DependencyUnavailable, Engine

CATEGORIES = ("Image", "Document", "Markdown/Text", "Audio", "Video")


class Registry:
    def __init__(self, engines: Iterable[Engine]):
        self.engines = {}
        self.unavailable_capabilities = []
        capabilities = []
        for engine in engines:
            if engine.engine_id in self.engines:
                raise ValueError("Duplicate conversion engine")
            if not engine.available():
                self.unavailable_capabilities.extend(engine.capabilities)
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
        for capability in self.unavailable_capabilities:
            if (capability.input_extension.lower() == source_extension.lower()
                    and capability.output_extension.lower() == output_extension.lower()):
                error = DependencyUnavailable(f"Required dependency for {capability.engine_id} is unavailable")
                error.engine_id = capability.engine_id
                raise error
        raise ConversionError("This conversion pair is unsupported")


def default_registry() -> Registry:
    from filewheel.converters.images import PillowEngine
    from filewheel.converters.markdown import MarkItDownEngine
    from filewheel.converters.office import LibreOfficeEngine
    from filewheel.converters.pdf_docx import PdfDocxEngine
    from filewheel.converters.pdf_images import PdfImagesEngine

    return Registry((PillowEngine(), PdfDocxEngine(), MarkItDownEngine(), LibreOfficeEngine(), PdfImagesEngine()))
