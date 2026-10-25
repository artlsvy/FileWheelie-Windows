"""Local Pillow conversions, explicit codec capabilities and immutable sources."""

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

_FORMATS = {
    ".png": "PNG",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".webp": "WEBP",
    ".heic": "HEIF",
    ".heif": "HEIF",
}


def _white_rgb(image):
    from PIL import Image

    rgba = image.convert("RGBA")
    try:
        rgb = Image.new("RGB", rgba.size, "white")
        with rgba.getchannel("A") as alpha:
            rgb.paste(rgba, mask=alpha)
        return rgb
    finally:
        rgba.close()


class PillowEngine:
    engine_id = "pillow"

    def __init__(
        self, *, quality: int = 90, max_pixels: int = 40_000_000, max_bytes: int = 100 * 1024 * 1024
    ):
        if type(quality) is not int or not 1 <= quality <= 95:
            raise ValueError("JPEG quality must be between 1 and 95")
        if (
            type(max_pixels) is not int
            or max_pixels < 1
            or type(max_bytes) is not int
            or max_bytes < 1
        ):
            raise ValueError("Image limits must be positive integers")
        self.quality, self.max_pixels, self.max_bytes = quality, max_pixels, max_bytes
        self.capabilities = self._capabilities()

    def _capabilities(self):
        if find_spec("PIL") is None:
            return ()
        from PIL import features

        jpeg = features.check("jpg")
        png = features.check("zlib")
        sources = ([".png"] if png else []) + ([".jpg", ".jpeg"] if jpeg else [])
        webp = features.check("webp")
        if webp:
            sources.append(".webp")
        if find_spec("pillow_heif") is not None:
            from pillow_heif import libheif_info, register_heif_opener

            decoders = libheif_info().get("decoders", {})
            if any("hevc" in str(value).lower() for value in decoders.values()):
                register_heif_opener(thumbnails=False)
                sources.extend((".heic", ".heif"))
        edges = []
        for source in sources:
            outputs = ([(".jpg", "JPEG")] if jpeg else [])
            outputs += [(".png", "PNG")] if png else []
            if webp and source not in (".heic", ".heif"):
                outputs.append((".webp", "WebP"))
            for output, label in outputs:
                if _FORMATS[source] != _FORMATS[output]:
                    edges.append(Capability(source, "Image", output, label, self.engine_id))
            # Validate generated PDF through the same local PDF backend used by
            # rasterization rather than claiming support from a filename/header.
            if jpeg and find_spec("pymupdf") is not None:
                edges.append(Capability(source, "Document", ".pdf", "PDF", self.engine_id))
        return tuple(edges)

    def available(self) -> bool:
        return bool(self.capabilities)

    def convert(
        self, source: Path, extension: str, workdir: Path, progress: Progress, cancel: Event | None
    ) -> tuple[EngineOutput, ...]:
        from PIL import Image, ImageOps

        check_cancel(cancel)
        if not any(
            cap.input_extension == source.suffix.lower() and cap.output_extension == extension
            for cap in self.capabilities
        ):
            raise ConversionError("Unsupported image conversion or unavailable codec")
        if source.stat().st_size > self.max_bytes:
            raise ConversionError("Image exceeds the input size limit")
        progress(0.15, "Reading image")
        with Image.open(source) as image:
            if image.format != _FORMATS[source.suffix.lower()]:
                raise ConversionError("The image content does not match its filename format")
            if min(image.size) < 1 or image.width * image.height > self.max_pixels:
                raise ConversionError("Image exceeds the pixel limit or is empty")
            if getattr(image, "n_frames", 1) != 1:
                raise ConversionError("Animated or multi-image input is not supported")
            image.load()
            check_cancel(cancel)
            progress(0.45, "Encoding image")
            with ImageOps.exif_transpose(image) as oriented:
                output = workdir / ("output" + extension)
                if extension in (".jpg", ".pdf"):
                    with _white_rgb(oriented) as rgb:
                        if extension == ".jpg":
                            rgb.save(output, format="JPEG", quality=self.quality, optimize=True)
                        else:
                            rgb.save(output, format="PDF", resolution=144.0)
                elif extension == ".png":
                    with oriented.convert("RGBA") as rgba:
                        rgba.save(output, format="PNG")
                elif extension == ".webp":
                    with oriented.convert("RGBA") as rgba:
                        rgba.save(output, format="WEBP", lossless=True, method=4)
        check_cancel(cancel)
        warnings = []
        if extension == ".jpg":
            warnings.append("JPEG is lossy; transparent pixels are composited onto white.")
        elif extension == ".pdf":
            warnings.append(
                "Image PDF is a single raster page, not editable text; transparency is white."
            )
        return (EngineOutput(output, source.with_suffix(extension).name, tuple(warnings)),)

    def validate(self, output: EngineOutput) -> None:
        if output.path.suffix.lower() == ".pdf":
            import pymupdf

            with pymupdf.open(output.path) as document:
                if not document.is_pdf or document.needs_pass or document.page_count != 1:
                    raise ConversionError("The generated image PDF failed validation")
                page = document[0]
                if page.rect.width <= 0 or page.rect.height <= 0 or not page.get_images():
                    raise ConversionError("The generated image PDF has invalid page content")
            return
        from PIL import Image

        expected = _FORMATS.get(output.path.suffix.lower())
        with Image.open(output.path) as image:
            if (
                expected is None
                or image.format != expected
                or min(image.size) <= 0
                or image.width * image.height > self.max_pixels
                or (expected == "JPEG" and image.mode != "RGB")
            ):
                raise ConversionError("The generated image failed validation")
            image.load()
