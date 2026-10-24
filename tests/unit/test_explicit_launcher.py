"""Portable launcher/controller/log checks; Windows context APIs are faked."""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path, PureWindowsPath
from unittest.mock import patch

from filewheel.core.controller import InvocationController
from filewheel.core.explicit_paths import FileCheck
from filewheel.platforms.windows import explicit_path_diagnostics as cli
from filewheel.platforms.windows.sendto import shortcut_plan


class ExplicitLauncherTests(unittest.TestCase):
    def run_cli(self, arguments):
        out, err = io.StringIO(), io.StringIO()
        with (
            patch.object(cli, "require_windows"),
            patch.object(cli, "cursor_point", return_value=(-100, 250)),
            patch.object(cli, "inspect_file", return_value=FileCheck(True, True)),
            redirect_stdout(out), redirect_stderr(err),
        ):
            code = cli.main(arguments)
        return code, out.getvalue(), err.getvalue()

    def test_cli_delimiter_unicode_spaces_and_controller_source(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / "case.jsonl"
            code, out, err = self.run_cli([
                "--enable", "--output", str(log), "--", r"C:\資料 æøå\100% & ! ^ report.txt",
            ])
            self.assertEqual(code, 0, err)
            record = json.loads(log.read_text(encoding="utf-8"))
            self.assertTrue(record["accepted"])
            self.assertEqual(record["path"], r"C:\資料 æøå\100% & ! ^ report.txt")
            self.assertEqual(record["point"], [-100, 250])
            self.assertEqual(record["source"], "shell_explicit")
            self.assertIn("diagnostic_only", out)

    def test_zero_multiple_and_relative_paths_reject_in_cli(self):
        for paths, rejection in (([], "expected_one_path"),
                                 ([r"C:\a.txt", r"C:\b.txt"], "expected_one_path"),
                                 (["relative.txt"], "absolute_local_path_required")):
            with self.subTest(paths=paths), tempfile.TemporaryDirectory() as folder:
                log = Path(folder) / "case.jsonl"
                code, _, _ = self.run_cli(["--enable", "--output", str(log), "--", *paths])
                self.assertEqual(code, 2)
                record = json.loads(log.read_text(encoding="utf-8"))
                self.assertFalse(record["accepted"])
                self.assertEqual(record["rejection"], rejection)
                self.assertIsNone(record["path"])

    def test_existing_log_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / "case.jsonl"
            log.write_text("original", encoding="utf-8")
            code, _, _ = self.run_cli(["--enable", "--output", str(log), "--", r"C:\a.txt"])
            self.assertEqual(code, 4)
            self.assertEqual(log.read_text(encoding="utf-8"), "original")

    def test_unique_logs_for_repeat_invocations(self):
        with tempfile.TemporaryDirectory() as folder:
            for _ in range(2):
                code, _, _ = self.run_cli(["--enable", "--output-dir", folder, "--", r"C:\a.txt"])
                self.assertEqual(code, 0)
            self.assertEqual(len(list(Path(folder).glob("invocation-*.jsonl"))), 2)

    def test_unicode_invocation_and_log_directory_work_with_ascii_console(self):
        class AsciiConsole(io.StringIO):
            def write(self, value):
                value.encode("ascii")  # Reproduce a strict legacy stdout codec.
                return super().write(value)

        with tempfile.TemporaryDirectory(prefix="filewheel-æøå-") as folder:
            console = AsciiConsole()
            with (
                patch.object(cli, "require_windows"),
                patch.object(cli, "cursor_point", return_value=(5, 6)),
                patch.object(cli, "inspect_file", return_value=FileCheck(True, True)),
                redirect_stdout(console),
            ):
                self.assertEqual(cli.main([
                    "--enable", "--output-dir", folder, "--", r"C:\資料 æøå\file.txt",
                ]), 0)
            record = json.loads(next(Path(folder).glob("*.jsonl")).read_text(encoding="utf-8"))
            self.assertEqual(record["path"], r"C:\資料 æøå\file.txt")
            self.assertIn("\\u", console.getvalue())

    def test_file_validation_goes_through_supplied_controller(self):
        controller = InvocationController()
        with patch.object(controller, "handle_explicit", wraps=controller.handle_explicit) as handle:
            record = cli.invocation_record(
                [r"C:\file.txt"], (5, 6), controller=controller,
                inspector=lambda path: FileCheck(True, False),
            )
        handle.assert_called_once()
        self.assertEqual(record["rejection"], "not_a_file")
        self.assertFalse(record["accepted"])

    def test_context_failure_is_reported_without_path_or_exception_text(self):
        out, err = io.StringIO(), io.StringIO()
        with (
            patch.object(cli, "require_windows"),
            patch.object(cli, "cursor_point", side_effect=OSError("private")),
            redirect_stdout(out), redirect_stderr(err),
        ):
            self.assertEqual(cli.main(["--enable", "--output-dir", "unused", "--", r"C:\a.txt"]), 3)
        self.assertNotIn("private", err.getvalue())
        self.assertFalse(out.getvalue())

    def test_import_does_not_require_uia_hooks_qt_or_comtypes(self):
        script = '''
import importlib.abc
import sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(("comtypes", "win32", "pythoncom", "PySide6")):
            raise AssertionError(fullname)
        if fullname.endswith((".hook", ".explorer_resolver", ".shell_view")):
            raise AssertionError(fullname)
sys.meta_path.insert(0, Block())
import filewheel.platforms.windows.explicit_path_diagnostics
import filewheel.platforms.windows.sendto
'''
        result = subprocess.run([sys.executable, "-c", script], env=os.environ,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class ShortcutPlanTests(unittest.TestCase):
    def test_direct_python_target_arguments_quoted_and_delimited(self):
        plan = shortcut_plan(PureWindowsPath(r"C:\My project & æøå"),
                             PureWindowsPath(r"C:\My project & æøå\.venv\Scripts\python.exe"))
        self.assertTrue(plan["target"].endswith(r"\python.exe"))
        self.assertEqual(plan["arguments"],
                         '-m filewheel.platforms.windows.explicit_path_diagnostics --enable '
                         '--output-dir "C:\\My project & æøå\\logs\\invocations" --')
        self.assertNotIn("cmd.exe", plan["target"])
        self.assertNotIn("powershell", plan["target"])
        self.assertNotIn("%1", plan["arguments"])

    def test_relative_project_or_executable_is_not_a_valid_plan(self):
        with self.assertRaises(ValueError):
            shortcut_plan(PureWindowsPath("relative"), PureWindowsPath(r"C:\python.exe"))

    def test_shortcut_script_is_packaged_next_to_manager(self):
        from filewheel.platforms.windows import sendto
        self.assertTrue(Path(sendto.__file__).with_name("sendto_shortcut.ps1").is_file())
