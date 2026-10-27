"""Portable Pandoc bundle contracts; these do not execute a Windows build."""

import hashlib
import json
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parents[2]
PACKAGING = ROOT / "packaging"


class PandocPackagingTests(unittest.TestCase):
    def test_build_option_is_opt_in_and_validates_before_build_and_after_complete_copy(self):
        script = (ROOT / "scripts/build-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("[string]$PandocDirectory = ''", script)
        guard = script.index("if ($PandocDirectory)")
        before = script.index("'filewheel.pandoc_tool', '--validate', $pandocSource")
        build = script.index("'PyInstaller'")
        copy = script.index(
            "Copy-Item -LiteralPath $pandocSource -Destination $pandocDestination -Recurse"
        )
        after = script.index("'filewheel.pandoc_tool', '--validate', $pandocDestination")
        self_test = script.index("$selfTest = Start-Process")
        self.assertLess(guard, before)
        self.assertLess(before, build)
        self.assertLess(build, copy)
        self.assertLess(copy, after)
        self.assertLess(after, self_test)
        self.assertIn("$pandocFull.Equals($distFull", script)
        self.assertIn("$pandocFull.StartsWith($distFull", script)
        self.assertIn("$distFull.StartsWith($pandocFull", script)
        self.assertLess(script.index("$pandocFull.Equals"), build)
        self.assertIn("$tools = Join-Path $distribution 'tools'", script)
        self.assertIn("$pandocDestination = Join-Path $tools 'pandoc'", script)
        self.assertIn("Refusing to replace an existing bundled Pandoc directory", script)
        self.assertIn("'filewheel.libreoffice_bundle', '--validate', $portableSource", script)
        self.assertIn("[PlatformID]::Win32NT", script)
        self.assertIn("sys.version_info[:2]==(3,14)", script)
        self.assertNotIn("Invoke-WebRequest", script)
        self.assertNotIn("tools/pandoc", (PACKAGING / "Filewheel.spec").read_text())

    def test_artifact_metadata_pins_optional_official_native_releases(self):
        metadata = json.loads((PACKAGING / "pandoc-artifacts.json").read_text())
        self.assertEqual(metadata["version"], "3.12.1")
        self.assertTrue(metadata["optional"])
        self.assertFalse(metadata["bundled_by_default"])
        self.assertFalse(metadata["automatic_download"])
        windows = metadata["artifacts"]["windows-x86_64"]
        self.assertEqual(windows["sha256"],
                         "6ef431cb20b2c24a0371fc19200dc49d452be54b1b5c9239f3462841ef53e587")
        self.assertEqual(windows["required_files"],
                         ["pandoc.exe", "COPYRIGHT.txt", "COPYING.rtf", "MANUAL.html"])
        for name, artifact in metadata["artifacts"].items():
            with self.subTest(artifact=name):
                self.assertTrue(artifact["url"].startswith(
                    "https://github.com/jgm/pandoc/releases/download/3.12.1/pandoc-3.12.1-"))
                self.assertRegex(artifact["sha256"], r"^[0-9a-f]{64}$")

    def test_manifest_inventories_exact_tool_bytes_relative_paths_and_licenses(self):
        module = runpy.run_path(str(PACKAGING / "build_manifest.py"))
        with tempfile.TemporaryDirectory() as folder:
            distribution = Path(folder)
            tool = distribution / "tools/pandoc"
            tool.mkdir(parents=True)
            contents = {
                "pandoc.exe": b"fake native executable" * 100000,
                "COPYRIGHT.txt": b"copyright evidence",
                "COPYING.rtf": b"license evidence",
                "MANUAL.html": b"manual evidence",
            }
            for name, content in contents.items():
                (tool / name).write_bytes(content)
            output = distribution / "BUILD-MANIFEST.json"
            arguments = ["build_manifest.py", "--root", str(ROOT), "--output", str(output)]
            # Native tool inventory must never execute the bundled executable.
            with patch.object(sys, "argv", arguments), patch.object(
                module["subprocess"], "run", side_effect=AssertionError("unexpected execution")
            ), patch.object(module["platform"], "platform", return_value="fake platform"
            ), patch.dict(module["main"].__globals__, {"git_value": lambda *_: None}):
                module["main"]()
            manifest = json.loads(output.read_text())
            inventory = manifest["native_tools"]["pandoc"]
            self.assertEqual(inventory["path"], "tools/pandoc")
            self.assertEqual(len(inventory["files"]), len(contents))
            for item in inventory["files"]:
                content = contents[Path(item["path"]).name]
                self.assertTrue(item["path"].startswith("tools/pandoc/"))
                self.assertEqual(item["size_bytes"], len(content))
                self.assertEqual(item["sha256"], hashlib.sha256(content).hexdigest())

    def test_manifest_absent_optional_tool_and_rejects_symlink(self):
        module = runpy.run_path(str(PACKAGING / "build_manifest.py"))
        with tempfile.TemporaryDirectory() as folder:
            distribution = Path(folder)
            self.assertEqual(module["native_tools"](distribution), {})
            tool = distribution / "tools/pandoc"
            tool.mkdir(parents=True)
            try:
                (tool / "pandoc.exe").symlink_to(distribution / "outside.exe")
            except (NotImplementedError, OSError):
                self.skipTest("symlinks unavailable")
            with self.assertRaisesRegex(ValueError, "symlinks"):
                module["native_tools"](distribution)


if __name__ == "__main__":
    unittest.main()


def test_pandoc_physical_source_check_precedes_rebuild():
    root = Path(__file__).resolve().parents[2]
    script = (root/'scripts/build-windows.ps1').read_text()
    physical_check = "'--validate', $pandocSource, '--output-root', $distribution"
    assert physical_check in script
    assert script.index(physical_check) < script.index("'-m', 'PyInstaller'")
