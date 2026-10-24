import os
import subprocess
import sys
import unittest

from filewheel.core.models import MouseEvent
from filewheel.platforms.windows.explorer_resolver import proven_target_from_evidence
from filewheel.platforms.windows.native import Native


class PlatformSeamTests(unittest.TestCase):
    def test_unproven_mapping_never_uses_name_or_selection(self):
        for evidence in (
            {}, {"selected_path": "C:/wrong.txt"},
            {"name": "report", "candidate_path": "C:/report.docx"},
            {"candidates": ["C:/report.docx", "C:/report.pdf"]},
        ):
            with self.subTest(evidence=evidence):
                self.assertIsNone(proven_target_from_evidence(MouseEvent(1, (0, 0), 1, 123), evidence))

    @unittest.skipIf(sys.platform == "win32", "Linux import isolation check")
    def test_imports_do_not_load_windows_dependencies(self):
        script = '''
import importlib.abc
import sys
class BlockWindows(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(("win32", "comtypes", "pythoncom")):
            raise AssertionError("Windows dependency imported: " + fullname)
sys.meta_path.insert(0, BlockWindows())
import filewheel.core.controller
import filewheel.platforms.windows.hook
import filewheel.platforms.windows.explorer_resolver
import filewheel.platforms.windows.diagnostics
'''
        result = subprocess.run([sys.executable, "-c", script], env=os.environ,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipIf(sys.platform == "win32", "Non-Windows guard check")
    def test_native_adapter_fails_explicitly_on_linux(self):
        with self.assertRaisesRegex(RuntimeError, "Windows 11"):
            Native()
