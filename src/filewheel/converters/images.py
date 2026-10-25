"""Pillow image conversions; decoded images are never saved over their source."""

from importlib.util import find_spec
from pathlib import Path
from threading import Event

from filewheel.converters.base import (
    Capability,
    ConversionError,
    EngineOutput,
    Progress,
    check_cancel,
)


class PillowEngine:
    engine_id = "pillow"
    capabilities = (Capability(".png", "Image", ".jpg", "JPEG", engine_id),)

    def __init__(self, *, quality: int = 90):
        if type(quality) is not int or not 1 <= quality <= 95:
            raise ValueError("JPEG quality must be between 1 and 95")
        self.quality = quality

    def available(self) -> bool:
        return find_spec("PIL") is not None

    def convert(self, source: Path, extension: str, workdir: Path,
                progress: Progress, cancel: Event | None) -> tuple[EngineOutput, ...]:
        from PIL import Image

        check_cancel(cancel)
        if source.suffix.lower() != ".png" or extension != ".jpg":
            raise ConversionError("Unsupported image conversion")
        progress(.15, "Reading image")
        with Image.open(source) as image:
            if image.format != "PNG":
                raise ConversionError("The input is not a PNG image")
            image.load()
            if getattr(image, "n_frames", 1) != 1:
                raise ConversionError("Animated PNG conversion is not supported")
            check_cancel(cancel)
            progress(.45, "Encoding JPEG")
            rgba = image.convert("RGBA")
            try:
                rgb = Image.new("RGB", rgba.size, "white")
                try:
                    rgb.paste(rgba, mask=rgba.getchannel("A"))
                    output = workdir / "output.jpg"
                    rgb.save(output, format="JPEG", quality=self.quality, optimize=True)
                finally:
                    rgb.close()
            finally:
                rgba.close()
        check_cancel(cancel)
        return (EngineOutput(output, source.with_suffix(extension).name),)

    def validate(self, output: EngineOutput) -> None:
        from PIL import Image

        with Image.open(output.path) as image:
            if image.format != "JPEG" or image.mode != "RGB" or min(image.size) <= 0:
                raise ConversionError("The generated JPEG failed validation")
            image.load()
