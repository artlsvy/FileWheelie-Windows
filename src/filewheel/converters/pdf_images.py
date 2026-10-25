"""Render every PDF page locally with bounded PyMuPDF rasterization."""

import math
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


class PdfImagesEngine:
    engine_id = "pymupdf-images"
    _possible_capabilities = (
        Capability(".pdf", "Image", ".png", "PNG pages", engine_id),
        Capability(".pdf", "Image", ".jpg", "JPEG pages", engine_id),
    )

    def __init__(
        self,
        *,
        dpi: int = 144,
        quality: int = 90,
        max_pages: int = 100,
        max_bytes: int = 50 * 1024 * 1024,
        max_pixels: int = 40_000_000,
    ):
        if type(dpi) is not int or not 36 <= dpi <= 600:
            raise ValueError("PDF raster DPI must be between 36 and 600")
        if type(quality) is not int or not 1 <= quality <= 95:
            raise ValueError("JPEG quality must be between 1 and 95")
        if any(type(value) is not int or value < 1 for value in (max_pages, max_bytes, max_pixels)):
            raise ValueError("PDF raster limits must be positive integers")
        self.capabilities = ()
        if find_spec("PIL") is not None:
            from PIL import features
            self.capabilities = tuple(c for c in self._possible_capabilities
                                      if features.check("zlib" if c.output_extension == ".png" else "jpg"))
        self.dpi, self.quality = dpi, quality
        self.max_pages, self.max_bytes, self.max_pixels = max_pages, max_bytes, max_pixels

    def available(self) -> bool:
        return bool(self.capabilities) and find_spec("pymupdf") is not None

    def convert(
        self, source: Path, extension: str, workdir: Path, progress: Progress, cancel: Event | None
    ) -> tuple[EngineOutput, ...]:
        import pymupdf

        check_cancel(cancel)
        if source.suffix.lower() != ".pdf" or extension not in (".png", ".jpg"):
            raise ConversionError("Unsupported PDF raster conversion")
        if source.stat().st_size > self.max_bytes:
            raise ConversionError("PDF exceeds the rasterization input size limit")
        progress(0.1, "Opening PDF pages")
        try:
            document = pymupdf.open(source)
        except (RuntimeError, ValueError) as error:
            raise ConversionError("The PDF is unreadable or corrupt") from error
        outputs = []
        with document:
            if not document.is_pdf or document.needs_pass:
                raise ConversionError("Input must be an unencrypted PDF")
            if not 0 < document.page_count <= self.max_pages:
                raise ConversionError("PDF exceeds the rasterization page limit or is empty")
            # Bound each allocation before asking MuPDF to create its pixel buffer.
            for page in document:
                check_cancel(cancel)
                width = math.ceil(page.rect.width * self.dpi / 72)
                height = math.ceil(page.rect.height * self.dpi / 72)
                if width < 1 or height < 1 or width * height > self.max_pixels:
                    raise ConversionError("PDF page exceeds the rasterization pixel limit")
            for index, page in enumerate(document):
                check_cancel(cancel)
                pixmap = page.get_pixmap(dpi=self.dpi, colorspace=pymupdf.csRGB, alpha=False)
                try:
                    output = workdir / f"page-{index + 1:03d}{extension}"
                    if extension == ".jpg":
                        pixmap.save(output, jpg_quality=self.quality)
                    else:
                        pixmap.save(output)
                finally:
                    del pixmap
                outputs.append(
                    EngineOutput(
                        output,
                        f"{source.stem}-page-{index + 1:03d}{extension}",
                        (
                            f"PDF pages are rasterized at {self.dpi} DPI; editable text and vector structure are lost.",
                        ),
                    )
                )
                progress(0.1 + 0.7 * (index + 1) / document.page_count, "Rendering PDF pages")
        check_cancel(cancel)
        return tuple(outputs)

    def validate(self, output: EngineOutput) -> None:
        from PIL import Image

        expected = {".png": "PNG", ".jpg": "JPEG"}.get(output.path.suffix.lower())
        with Image.open(output.path) as image:
            if (
                expected is None
                or image.format != expected
                or image.mode != "RGB"
                or min(image.size) < 1
                or image.width * image.height > self.max_pixels
            ):
                raise ConversionError("Generated PDF page image failed validation")
            image.load()
