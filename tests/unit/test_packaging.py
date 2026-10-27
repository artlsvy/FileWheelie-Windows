"""Portable packaging contracts; these checks do not claim a Windows EXE build."""

import ast
import json
import os
import re
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parents[2]
PACKAGING = ROOT / "packaging"


class PackagingTests(unittest.TestCase):
    def test_frozen_entry_freeze_support_precedes_application_import(self):
        tree = ast.parse((PACKAGING / "entry.py").read_text(encoding="utf-8"))
        freeze = next(
            index
            for index, statement in enumerate(tree.body)
            if isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Call)
            and isinstance(statement.value.func, ast.Attribute)
            and statement.value.func.attr == "freeze_support"
        )
        application = next(
            index
            for index, statement in enumerate(tree.body)
            if isinstance(statement, ast.ImportFrom) and statement.module == "filewheel.app"
        )
        self.assertLess(freeze, application)
        self.assertNotIn("PySide6", (PACKAGING / "entry.py").read_text())

    def test_spec_is_onedir_windowed_with_engine_assets_and_no_unused_webengine(self):
        text = (PACKAGING / "Filewheel.spec").read_text(encoding="utf-8")
        tree = ast.parse(text)
        self.assertIn('sys.platform != "win32"', text)
        self.assertIn("(3, 14)", text)
        for module in (
            "pillow_heif",
            "pymupdf",
            "pdf2docx",
            "markitdown",
            "magika",
            "cv2",
            "docx",
            "pptx",
            "pdfminer",
            "onnxruntime",
            "comtypes",
        ):
            self.assertIn('"' + module + '"', text)
        self.assertIn("sendto_shortcut.ps1", text)
        self.assertIn('"filewheel/platforms/windows"', text)
        self.assertIn('"packaging/runtime_hook.py"', text)
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ]
        exe = next(node for node in calls if node.func.id == "EXE")
        keywords = {keyword.arg: keyword.value for keyword in exe.keywords}
        self.assertFalse(ast.literal_eval(keywords["console"]))
        self.assertEqual(ast.unparse(keywords["exclude_binaries"]), 'not onefile')
        self.assertEqual(ast.literal_eval(keywords["contents_directory"]), "_internal")
        self.assertTrue(any(node.func.id == "COLLECT" for node in calls))
        analysis = next(node for node in calls if node.func.id == "Analysis")
        excludes = next(keyword.value for keyword in analysis.keywords if keyword.arg == "excludes")
        self.assertIn("PySide6.QtWebEngineCore", ast.literal_eval(excludes))
        self.assertIn("FILEWHEEL_BUNDLE_", text)

    def test_runtime_hook_sets_private_writable_cache_without_loading_com_or_qt(self):
        text = (PACKAGING / "runtime_hook.py").read_text(encoding="utf-8")
        imports = [
            node
            for node in ast.walk(ast.parse(text))
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        modules = [
            node.module if isinstance(node, ast.ImportFrom) else node.names[0].name
            for node in imports
        ]
        self.assertFalse(
            any(module.startswith(("comtypes", "PySide6", "onnxruntime")) for module in modules)
        )
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.dict(os.environ, {"LOCALAPPDATA": folder}),
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", folder, create=True),
            patch.object(sys, "platform", "win32"),
        ):
            runpy.run_path(str(PACKAGING / "runtime_hook.py"))
            self.assertEqual(os.environ["ORT_DISABLE_TELEMETRY"], "1")
            cache = Path(os.environ["FILEWHEEL_COMTYPES_CACHE"])
            self.assertEqual(cache, Path(folder) / "Filewheel/comtypes_cache/py314")
            self.assertTrue(cache.is_dir())

    def test_every_locked_dependency_has_exact_version_and_single_wheel_hash(self):
        lock = (PACKAGING / "windows-py314.lock").read_text(encoding="utf-8")
        logical = lock.replace("\\\n", " ")
        requirements = [
            line.strip()
            for line in logical.splitlines()
            if line.strip() and not line.startswith("#")
        ]
        parsed = {}
        for line in requirements:
            match = re.fullmatch(
                r"([A-Za-z0-9_.-]+)(\[[^]]+\])?==([^\s]+)\s+--hash=sha256:([0-9a-f]{64})", line
            )
            self.assertIsNotNone(match, line)
            name = re.sub(r"[-_.]+", "-", match[1]).lower()
            self.assertNotIn(name, parsed)
            parsed[name] = (match[3], match[2])
        self.assertGreaterEqual(len(parsed), 54)
        self.assertEqual(parsed["pyinstaller"][0], "6.22.3")
        self.assertEqual(parsed["markitdown"], ("0.1.9", "[docx,pdf,pptx,xlsx]"))
        for conditional in ("pefile", "pywin32-ctypes", "colorama"):
            self.assertIn(conditional, parsed)

    def test_build_script_guards_platform_interpreter_environment_and_frozen_self_test(self):
        text = (ROOT / "scripts/build-windows.ps1").read_text(encoding="utf-8")
        for required in (
            "[PlatformID]::Win32NT",
            "sys.version_info[:2]==(3,14)",
            "struct.calcsize('P')==8",
            "--require-hashes",
            "--only-binary=:all:",
            "--no-build-isolation",
            "--no-deps",
            "--self-test",
            "-PassThru",
            "WaitForExit(180000)",
            "DEPENDENCIES.txt",
            "BUILD-MANIFEST.json",
            "--validate",
        ):
            self.assertIn(required, text)
        self.assertIn("refusing to overwrite", text)
        self.assertNotIn("Remove-Item", text)
        self.assertNotIn("--onefile", text)
        self.assertLess(text.index("--validate"), text.index("'PyInstaller'"))
        self.assertIn("tools", text)
        self.assertIn("Copy-Item -LiteralPath $portableSource", text)
        self.assertIn("$distFull.StartsWith($sourceFull", text)
        self.assertIn("$sourceFull.StartsWith($distFull", text)

    def test_build_manifest_records_lock_and_exclusive_output(self):
        module = runpy.run_path(str(PACKAGING / "build_manifest.py"))
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "manifest.json"
            args = ["build_manifest.py", "--root", str(ROOT), "--output", str(output)]
            with patch.object(sys, "argv", args):
                module["main"]()
            manifest = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(manifest["layout"], "onedir")
            self.assertTrue(manifest["experimental_mouse3_default"])
            self.assertRegex(manifest["lock_sha256"], r"^[0-9a-f]{64}$")
            self.assertIn("python", manifest)
            with patch.object(sys, "argv", args), self.assertRaises(FileExistsError):
                module["main"]()

    def test_quick_scene_and_native_qml_hooks_are_included(self):
        import tomllib
        from importlib.resources import files
        package = files('filewheel.ui').joinpath('qml')
        self.assertTrue(package.joinpath('GlassWheel.qml').is_file())
        self.assertTrue(package.joinpath('Lens.qml').is_file())
        self.assertTrue(package.joinpath('ProgressSurface.qml').is_file())
        self.assertIn('Lens {', package.joinpath('GlassWheel.qml').read_text())
        metadata = tomllib.loads((ROOT / 'pyproject.toml').read_text())
        self.assertIn('qml/*.qml', metadata['tool']['setuptools']['package-data']['filewheel.ui'])
        spec = (PACKAGING / 'Filewheel.spec').read_text()
        self.assertIn('"PySide6.QtQuick"', spec)
        self.assertIn('"PySide6.QtQml"', spec)
        self.assertIn('"filewheel/ui/qml"', spec)
