"""Portable checks of the opt-in probe's exact-URI message boundary."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "bridge_receiver", Path(__file__).with_name("receiver.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReceiverTests(unittest.TestCase):
    def test_exact_uri_across_tabs_unicode_and_spaces(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            files = set()
            for directory in ("Tab A", "Tab B"):
                (root / directory).mkdir()
                file = root / directory / "résumé æøå % &.txt"
                file.write_text("unchanged")
                files.add(file)
            for file in files:
                path, sequence = module.validate(
                    ("a" * 64, file.as_uri(), 1, 100),
                    token="a" * 64,
                    previous=0,
                    now=101,
                    fixtures=files,
                )
                self.assertEqual(path, file)
                self.assertEqual(sequence, 1)
                self.assertEqual(file.read_text(), "unchanged")

    def test_rejects_forgery_replay_age_future_nonlocal_and_invalid_payloads(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "file.txt"
            file.write_text("test")
            valid = ("a" * 64, file.as_uri(), 2, 100)
            bad = [
                None,
                (),
                ("a" * 64, file.as_uri()),
                ("x" * 64, file.as_uri(), 2, 100),
                ("æ" * 64, file.as_uri(), 2, 100),
                ("a" * 64, file.as_uri(), 1, 100),
                ("a" * 64, file.as_uri(), True, 100),
                ("a" * 64, file.as_uri(), 2, -3_000_000_000),
                ("a" * 64, file.as_uri(), 2, 300),
                ("a" * 64, "https://example.com/file", 2, 100),
                ("a" * 64, "file://remote/path", 2, 100),
                ("a" * 64, file.as_uri() + "?q=1", 2, 100),
                ("a" * 64, Path(folder).as_uri(), 2, 100),
                ("a" * 64, (Path(folder) / "missing").as_uri(), 2, 100),
            ]
            for payload in bad:
                with self.subTest(payload=payload), self.assertRaises((ValueError, UnicodeError)):
                    module.validate(payload, token="a" * 64, previous=1, now=200, fixtures={file})
            self.assertEqual(
                module.validate(valid, token="a" * 64, previous=1, now=200, fixtures={file})[0],
                file,
            )

    def test_symlink_and_deleted_fixture_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            file = root / "source"
            file.write_text("test")
            link = root / "link"
            link.symlink_to(file)
            with self.assertRaises(ValueError):
                module.validate(
                    ("a" * 64, link.as_uri(), 1, 100),
                    token="a" * 64,
                    previous=0,
                    now=101,
                    fixtures={link},
                )
            file.unlink()
            with self.assertRaises(ValueError):
                module.validate(
                    ("a" * 64, file.as_uri(), 1, 100),
                    token="a" * 64,
                    previous=0,
                    now=101,
                    fixtures={file},
                )


if __name__ == "__main__":
    unittest.main()
