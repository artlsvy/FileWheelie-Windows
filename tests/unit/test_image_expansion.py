"""Real image codecs and multi-page PDF raster output through the shared manager."""

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import patch

from filewheel.converters import ConversionCancelled, ConversionError, ConversionManager, Registry
from filewheel.converters.images import PillowEngine
from filewheel.converters.pdf_images import PdfImagesEngine

PIL = importlib.util.find_spec("PIL") is not None
PDF = importlib.util.find_spec("pymupdf") is not None
HEIF = importlib.util.find_spec("pillow_heif") is not None


@unittest.skipUnless(PIL, "Pillow optional dependency unavailable")
class ImageExpansionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.folder = Path(self.temporary.name)
        self.engine = PillowEngine()
        self.manager = ConversionManager(Registry((self.engine,)))

    def tearDown(self):
        self.temporary.cleanup()

    def make_image(self, suffix, *, mode="RGBA", color=(200, 60, 30, 120)):
        from PIL import Image

        source = self.folder / ("résumé image" + suffix)
        with Image.new(mode, (32, 24), color) as image:
            image.save(
                source,
                format={".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP"}[suffix],
            )
        return source

    def test_all_png_jpeg_webp_pairs_dimensions_format_and_source_hash(self):
        from PIL import Image, features

        if not features.check("webp"):
            self.skipTest("WebP codec unavailable")
        pairs = (
            (".png", ".jpg"),
            (".png", ".webp"),
            (".jpg", ".png"),
            (".jpg", ".webp"),
            (".webp", ".png"),
            (".webp", ".jpg"),
            (".jpeg", ".png"),
        )
        for source_ext, output_ext in pairs:
            with self.subTest(pair=(source_ext, output_ext)):
                mode, color = (
                    ("RGB", (20, 100, 180))
                    if source_ext in (".jpg", ".jpeg")
                    else ("RGBA", (200, 60, 30, 120))
                )
                source = self.make_image(source_ext, mode=mode, color=color)
                digest = hashlib.sha256(source.read_bytes()).digest()
                result = self.manager.convert(source, output_ext)
                with Image.open(result.path) as output:
                    output.load()
                    self.assertEqual(output.size, (32, 24))
                    self.assertEqual(
                        output.format, {".png": "PNG", ".jpg": "JPEG", ".webp": "WEBP"}[output_ext]
                    )
                self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), digest)

    def test_png_webp_roundtrip_preserves_transparency(self):
        from PIL import Image, features

        if not features.check("webp"):
            self.skipTest("WebP codec unavailable")
        source = self.make_image(".png")
        webp = self.manager.convert(source, ".webp").path
        png = self.manager.convert(webp, ".png").path
        with Image.open(png) as output:
            self.assertEqual(output.getpixel((5, 5)), (200, 60, 30, 120))

    def test_animated_image_and_renamed_content_reject(self):
        from PIL import Image

        source = self.folder / "animated.png"
        with (
            Image.new("RGBA", (10, 10), "red") as first,
            Image.new("RGBA", (10, 10), "blue") as second,
        ):
            first.save(source, format="PNG", save_all=True, append_images=[second], duration=100)
        with self.assertRaisesRegex(ConversionError, "Animated"):
            self.manager.convert(source, ".jpg")
        renamed = self.folder / "wrong.png"
        with Image.new("RGB", (10, 10)) as image:
            image.save(renamed, format="JPEG")
        with self.assertRaisesRegex(ConversionError, "format"):
            self.manager.convert(renamed, ".jpg")
        self.assertFalse(list(self.folder.glob("*.jpg")))
        self.assertFalse(list(self.folder.glob(".filewheel-*")))

    def test_missing_png_or_jpeg_codec_hides_dependent_pairs(self):
        for absent, extensions in (("zlib", {".png"}), ("jpg", {".jpg", ".jpeg"})):
            with self.subTest(codec=absent), patch("PIL.features.check",
                    side_effect=lambda name, absent=absent: name != absent):
                capabilities = PillowEngine().capabilities
            self.assertFalse(any(c.input_extension in extensions or c.output_extension in extensions
                                 for c in capabilities))
            if absent == "jpg":
                self.assertFalse(any(c.output_extension == ".pdf" for c in capabilities))

    def test_missing_webp_and_heif_hide_only_their_pairs(self):
        original_find = importlib.util.find_spec
        with (
            patch("PIL.features.check", side_effect=lambda name: name != "webp"),
            patch(
                "filewheel.converters.images.find_spec",
                side_effect=lambda name: None if name == "pillow_heif" else original_find(name),
            ),
        ):
            capabilities = PillowEngine().capabilities
        self.assertFalse(
            any(
                c.input_extension in (".webp", ".heic", ".heif") or c.output_extension == ".webp"
                for c in capabilities
            )
        )
        self.assertTrue(
            any(c.input_extension == ".png" and c.output_extension == ".jpg" for c in capabilities)
        )

    def test_pixel_limit_rejects_before_image_decode(self):
        source = self.make_image(".png")
        manager = ConversionManager(Registry((PillowEngine(max_pixels=1),)))
        with self.assertRaisesRegex(ConversionError, "pixel limit"):
            manager.convert(source, ".jpg")
        self.assertFalse(list(self.folder.glob("*.jpg")))

    @unittest.skipUnless(HEIF, "pillow-heif optional dependency unavailable")
    def test_actual_heic_to_png_jpeg_preserves_dimensions_source(self):
        import pillow_heif
        from PIL import Image

        if not pillow_heif.libheif_info().get("HEIF"):
            self.skipTest("HEIC fixture encoder unavailable")
        source = self.folder / "photo.heic"
        with Image.new("RGB", (32, 24), (60, 120, 180)) as image:
            heif = pillow_heif.from_pillow(image)
            heif.save(source, quality=90)
        digest = hashlib.sha256(source.read_bytes()).digest()
        for extension in (".jpg", ".png"):
            result = self.manager.convert(source, extension)
            with Image.open(result.path) as output:
                output.load()
                self.assertEqual(output.size, (32, 24))
        self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), digest)

    @unittest.skipUnless(PDF, "PyMuPDF optional dependency unavailable")
    def test_images_to_pdf_are_readable_single_pages_with_white_alpha(self):
        import pymupdf

        source = self.make_image(".png", color=(255, 0, 0, 0))
        result = self.manager.convert(source, ".pdf")
        with pymupdf.open(result.path) as document:
            self.assertEqual(document.page_count, 1)
            page = document[0]
            self.assertAlmostEqual(page.rect.width / page.rect.height, 32 / 24)
            pixmap = page.get_pixmap(alpha=False)
            self.assertTrue(all(value >= 245 for value in pixmap.pixel(5, 5)))
        self.assertTrue(result.warnings)


@unittest.skipUnless(PIL and PDF, "Pillow/PyMuPDF optional dependencies unavailable")
class PdfImageExpansionTests(unittest.TestCase):
    def setUp(self):
        import pymupdf

        self.temporary = tempfile.TemporaryDirectory()
        self.folder = Path(self.temporary.name)
        self.source = self.folder / "résumé source.pdf"
        with pymupdf.open() as document:
            for index in range(3):
                page = document.new_page(width=200, height=120)
                page.insert_text((10, 30), f"Page {index + 1}")
            document.save(self.source)
        self.engine = PdfImagesEngine()
        self.manager = ConversionManager(Registry((self.engine,)))

    def tearDown(self):
        self.temporary.cleanup()

    def test_all_pages_png_jpeg_valid_dimensions_collision_and_source_hash(self):
        from PIL import Image

        digest = hashlib.sha256(self.source.read_bytes()).digest()
        for extension in (".png", ".jpg"):
            existing = self.folder / (self.source.stem + "-page-001" + extension)
            existing.write_bytes(b"preserve")
            result = self.manager.convert(self.source, extension)
            self.assertEqual(len(result.outputs), 3)
            self.assertTrue(result.outputs[0].name.endswith(f"-page-001 (2){extension}"))
            for output in result.outputs:
                with Image.open(output) as image:
                    image.load()
                    self.assertEqual(image.size, (400, 240))
                    self.assertEqual(image.mode, "RGB")
            self.assertEqual(existing.read_bytes(), b"preserve")
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).digest(), digest)
        self.assertFalse(list(self.folder.glob(".filewheel-*")))

    def test_cancel_after_page_render_cleans_all_staged_outputs(self):
        event = Event()

        def progress(value, message):
            if value > 0.1:
                event.set()

        with self.assertRaises(ConversionCancelled):
            self.manager.convert(self.source, ".png", progress=progress, cancel=event)
        self.assertEqual(list(self.folder.iterdir()), [self.source])

    def test_corrupt_pdf_page_and_pixel_limits_leave_no_outputs(self):
        for engine in (
            PdfImagesEngine(max_pages=1),
            PdfImagesEngine(max_pixels=1),
            PdfImagesEngine(max_bytes=1),
        ):
            with self.assertRaisesRegex(ConversionError, "limit"):
                ConversionManager(Registry((engine,))).convert(self.source, ".png")
        self.source.write_bytes(b"corrupt")
        with self.assertRaisesRegex(ConversionError, "corrupt"):
            self.manager.convert(self.source, ".jpg")
        self.assertEqual(list(self.folder.iterdir()), [self.source])

    def test_failed_second_page_render_cleans_partial_first_page(self):
        import pymupdf

        real_get = pymupdf.Page.get_pixmap
        calls = []

        def fail_second(page, *args, **kwargs):
            calls.append(page.number)
            if len(calls) == 2:
                raise RuntimeError("render failed")
            return real_get(page, *args, **kwargs)

        with (
            patch.object(pymupdf.Page, "get_pixmap", fail_second),
            self.assertRaises(ConversionError),
        ):
            self.manager.convert(self.source, ".png")
        self.assertEqual(list(self.folder.iterdir()), [self.source])
