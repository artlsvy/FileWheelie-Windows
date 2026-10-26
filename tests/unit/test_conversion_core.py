"""Real Pillow output and adversarial shared publication tests on native paths."""

import hashlib
import importlib.util
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from unittest.mock import patch

from filewheel.converters import (
    Capability,
    ConversionCancelled,
    ConversionError,
    ConversionManager,
    EngineOutput,
    Registry,
)
from filewheel.converters.images import PillowEngine

PIL_AVAILABLE = importlib.util.find_spec("PIL") is not None


class FakeEngine:
    engine_id = "fake"
    capabilities = (Capability(".abc", "Document", ".xyz", "XYZ", engine_id),)

    def available(self):
        return True

    def convert(self, source, extension, workdir, progress, cancel):
        output = workdir / "output.xyz"
        output.write_bytes(b"validated output")
        return (EngineOutput(output, source.with_suffix(extension).name),)

    def validate(self, output):
        pass


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.folder = Path(self.temporary.name)
        self.source = self.folder / "source.abc"
        self.source.write_bytes(b"original")
        self.engine = FakeEngine()
        self.manager = ConversionManager(Registry((self.engine,)))

    def tearDown(self):
        self.temporary.cleanup()

    def test_collision_never_replaces_existing_or_source(self):
        existing = self.folder / "source.xyz"
        existing.write_bytes(b"existing")
        result = self.manager.convert(self.source, ".xyz")
        self.assertEqual(result.path.name, "source (2).xyz")
        self.assertEqual(existing.read_bytes(), b"existing")
        self.assertEqual(self.source.read_bytes(), b"original")
        self.assertFalse(list(self.folder.glob(".filewheel-*")))

    def test_publication_fence_runs_after_validation_before_any_link(self):
        events = []
        real_link = os.link
        def link(source, destination):
            events.append("link")
            return real_link(source, destination)
        with (patch.object(self.engine, "validate", side_effect=lambda output: events.append("validate")),
              patch("filewheel.converters.manager.os.link", side_effect=link)):
            self.manager.convert(self.source, ".xyz", before_publish=lambda: events.append("permit"))
        self.assertEqual(events, ["validate", "permit", "link"])

    def test_multi_output_fence_runs_once_after_every_validation(self):
        events = []
        def generate(source, extension, workdir, progress, cancel):
            outputs = []
            for index in range(2):
                path = workdir / f"page-{index}.xyz"
                path.write_bytes(b"output")
                outputs.append(EngineOutput(path, path.name))
            return tuple(outputs)
        with (patch.object(self.engine, "convert", side_effect=generate),
              patch.object(self.engine, "validate", side_effect=lambda output: events.append("validate"))):
            self.manager.convert(self.source, ".xyz", before_publish=lambda: events.append("permit"))
        self.assertEqual(events, ["validate", "validate", "permit"])

    def test_fence_failure_or_cancellation_never_publishes(self):
        for cancelled in (False, True):
            event = Event()
            def fence(cancelled=cancelled, event=event):
                if cancelled:
                    event.set()
                else:
                    raise RuntimeError("supervisor disconnected")
            with self.subTest(cancelled=cancelled), self.assertRaises(ConversionError):
                self.manager.convert(self.source, ".xyz", cancel=event, before_publish=fence)
            self.assertEqual(list(self.folder.iterdir()), [self.source])

    def test_validation_failure_does_not_request_publication(self):
        with (patch.object(self.engine, "validate", side_effect=ConversionError("invalid")),
              patch("filewheel.converters.manager.os.link") as link,
              self.assertRaises(ConversionError)):
            self.manager.convert(self.source, ".xyz", before_publish=link)
        link.assert_not_called()

    def test_supervisor_workspace_is_retained_on_success_and_failure(self):
        workspace = self.folder / ".filewheel-owned"
        workspace.mkdir()
        self.manager.convert(self.source, ".xyz", workspace=workspace)
        self.assertTrue((workspace / "output.xyz").is_file())
        with (patch.object(self.engine, "validate", side_effect=ConversionError("invalid")),
              self.assertRaises(ConversionError)):
            self.manager.convert(self.source, ".xyz", workspace=workspace)
        self.assertTrue(workspace.is_dir())
        self.assertEqual(self.source.read_bytes(), b"original")
        self.assertEqual((self.folder / "source.xyz").read_bytes(), b"validated output")

    def test_unsafe_supervisor_workspaces_reject_before_engine(self):
        ordinary = self.folder / "ordinary"
        ordinary.mkdir()
        file = self.folder / ".filewheel-file"
        file.write_bytes(b"keep")
        outside = self.folder / "nested" / ".filewheel-child"
        outside.mkdir(parents=True)
        paths = [Path(".filewheel-relative"), ordinary, file, outside,
                 self.folder / ".filewheel-missing"]
        link = self.folder / ".filewheel-link"
        try:
            link.symlink_to(ordinary, target_is_directory=True)
            paths.append(link)
        except OSError:
            pass
        with patch.object(self.engine, "convert") as convert:
            for path in paths:
                with self.subTest(path=path), self.assertRaises(ConversionError):
                    self.manager.convert(self.source, ".xyz", workspace=path)
        convert.assert_not_called()
        self.assertEqual(file.read_bytes(), b"keep")

    def test_atomic_concurrent_collisions(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.manager.convert(self.source, ".xyz"), range(4)))
        self.assertEqual(len({result.path for result in results}), 4)
        self.assertTrue(all(result.path.read_bytes() == b"validated output" for result in results))
        self.assertFalse(list(self.folder.glob(".filewheel-*")))

    def test_failure_cleans_stage_and_preserves_existing(self):
        def fail(source, extension, workdir, progress, cancel):
            (workdir / "partial.xyz").write_bytes(b"partial")
            raise ValueError("corrupt")
        with patch.object(self.engine, "convert", side_effect=fail), self.assertRaises(ConversionError):
            self.manager.convert(self.source, ".xyz")
        self.assertEqual(list(self.folder.iterdir()), [self.source])

    def test_invalid_output_never_published(self):
        with patch.object(self.engine, "validate", side_effect=ConversionError("invalid")), self.assertRaises(ConversionError):
            self.manager.convert(self.source, ".xyz")
        self.assertEqual(list(self.folder.iterdir()), [self.source])

    def test_multi_output_failure_rolls_back_only_new_files(self):
        real_link = os.link
        calls = []
        def generate(source, extension, workdir, progress, cancel):
            outputs = []
            for index in range(2):
                path = workdir / f"page-{index}.xyz"
                path.write_bytes(b"output")
                outputs.append(EngineOutput(path, path.name))
            return tuple(outputs)
        def fail_second(source, destination):
            calls.append(destination)
            if len(calls) == 2:
                raise OSError("disk failure")
            return real_link(source, destination)
        with (patch.object(self.engine, "convert", side_effect=generate),
              patch("filewheel.converters.manager.os.link", side_effect=fail_second), self.assertRaises(ConversionError)):
            self.manager.convert(self.source, ".xyz")
        self.assertEqual(list(self.folder.iterdir()), [self.source])

    def test_no_post_publication_stat_failure_leaves_output(self):
        original_stat = Path.stat
        destination = self.folder / "source.xyz"
        def reject_destination_stat(path, *args, **kwargs):
            if path == destination:
                raise OSError("post-publication stat denied")
            return original_stat(path, *args, **kwargs)
        with patch.object(Path, "stat", reject_destination_stat):
            result = self.manager.convert(self.source, ".xyz")
        self.assertEqual(result.path.read_bytes(), b"validated output")

    def test_cancellation_before_and_after_encoding(self):
        for after_encode in (False, True):
            event = Event()
            if not after_encode:
                event.set()
            def progress(fraction, message, event=event):
                if fraction == .9:
                    event.set()
            with self.assertRaises(ConversionCancelled):
                self.manager.convert(self.source, ".xyz", progress=progress, cancel=event)
            self.assertEqual(list(self.folder.iterdir()), [self.source])

    def test_missing_directory_relative_and_symlink_reject(self):
        for path in (self.folder / "absent.abc", self.folder, Path("source.abc")):
            with self.subTest(path=path), self.assertRaises(ConversionError):
                self.manager.convert(path, ".xyz")
        link = self.folder / "link.abc"
        try:
            link.symlink_to(self.source)
        except OSError:
            self.skipTest("symlinks unavailable")
        with self.assertRaises(ConversionError):
            self.manager.convert(link, ".xyz")

    def test_unsafe_engine_output_path_rejects(self):
        with patch.object(self.engine, "convert", return_value=(EngineOutput(self.source, "../bad.xyz"),)), self.assertRaises(ConversionError):
            self.manager.convert(self.source, ".xyz")
        self.assertEqual(list(self.folder.iterdir()), [self.source])

    def test_unavailable_engine_hidden_and_unsupported_pair_rejects(self):
        with patch.object(self.engine, "available", return_value=False):
            registry = Registry((self.engine,))
        self.assertEqual(registry.capabilities, ())
        with self.assertRaises(ConversionError):
            ConversionManager(registry).convert(self.source, ".xyz")


@unittest.skipUnless(PIL_AVAILABLE, "Pillow optional dependency unavailable")
class PillowConversionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.folder = Path(self.temporary.name)
        self.manager = ConversionManager(Registry((PillowEngine(),)))

    def tearDown(self):
        self.temporary.cleanup()

    def make_png(self, mode, color, name="sample.png"):
        from PIL import Image
        source = self.folder / name
        with Image.new(mode, (32, 24), color) as image:
            image.save(source, format="PNG")
        return source

    def test_rgb_rgba_grayscale_valid_dimensions_and_unchanged_source(self):
        from PIL import Image
        for index, (mode, color) in enumerate((("RGB", (220, 20, 40)),
                                                ("RGBA", (220, 20, 40, 150)), ("L", 130))):
            with self.subTest(mode=mode):
                source = self.make_png(mode, color, f"sample-{index}.png")
                before = hashlib.sha256(source.read_bytes()).digest()
                progress = []
                result = self.manager.convert(source, ".jpg", progress=lambda value, _, progress=progress: progress.append(value))
                with Image.open(result.path) as output:
                    output.load()
                    self.assertEqual(output.format, "JPEG")
                    self.assertEqual(output.mode, "RGB")
                    self.assertEqual(output.size, (32, 24))
                self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), before)
                self.assertEqual(progress[0], 0.0)
                self.assertEqual(progress[-1], 1.0)

    def test_transparency_has_white_background(self):
        from PIL import Image
        source = self.make_png("RGBA", (255, 0, 0, 0))
        with Image.open(self.manager.convert(source, ".jpg").path) as output:
            self.assertTrue(all(channel >= 250 for channel in output.getpixel((10, 10))))

    def test_unicode_spaces_and_uppercase_extension(self):
        source = self.make_png("RGB", "blue", "æøå image.PNG")
        result = self.manager.convert(source, ".JPG")
        self.assertEqual(result.path.name, "æøå image.jpg")
        self.assertIn("Image", self.manager.registry.categories(source))
        self.assertEqual(self.manager.registry.formats(source, "Image")[0].label, "JPEG")

    def test_corrupt_and_renamed_non_png_reject_without_output(self):
        from PIL import Image
        source = self.folder / "corrupt.png"
        source.write_bytes(b"not png")
        with self.assertRaises(ConversionError):
            self.manager.convert(source, ".jpg")
        with Image.new("RGB", (10, 10)) as image:
            image.save(source, format="JPEG")
        with self.assertRaises(ConversionError):
            self.manager.convert(source, ".jpg")
        self.assertEqual(list(self.folder.iterdir()), [source])

    def test_quality_guard(self):
        for quality in (0, 96, True):
            with self.assertRaises(ValueError):
                PillowEngine(quality=quality)
