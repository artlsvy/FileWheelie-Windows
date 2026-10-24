"""GUI integration rejects invalid argv before importing optional Qt."""
import io
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import PureWindowsPath
from unittest.mock import patch

from filewheel.core.explicit_paths import FileCheck
from filewheel.core.models import TargetResolution
from filewheel.platforms.windows import explicit_path_diagnostics as cli
from filewheel.platforms.windows.sendto import shortcut_plan


class GuiLauncherTests(unittest.TestCase):
    def invoke(self, paths, check=FileCheck(True, True), preview=None):
        with (patch.object(cli, 'require_windows'),
              patch.object(cli, 'cursor_point', return_value=(-500, 200)),
              patch.object(cli, 'inspect_file', return_value=check),
              patch.object(cli, 'show_preview', return_value=preview) as show,
              redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO())):
            result = cli.main(['--gui', '--', *paths])
        return result, show

    def test_valid_gui_passes_controller_target_with_unicode_and_point(self):
        result, show = self.invoke([r'C:\資料\a file.png'])
        self.assertEqual(result, 0)
        target = show.call_args.args[0]
        self.assertIsInstance(target, TargetResolution)
        self.assertEqual(target.source, 'shell_explicit')
        self.assertEqual(target.point, (-500, 200))
        self.assertEqual(str(target.path), r'C:\資料\a file.png')

    def test_rejected_paths_never_enter_gui(self):
        for paths, check in (([], FileCheck(True, True)),
                             ([r'C:\a.png', r'C:\b.png'], FileCheck(True, True)),
                             (['relative.png'], FileCheck(True, True)),
                             ([r'C:\folder'], FileCheck(True, False)),
                             ([r'C:\absent.png'], FileCheck(False, False))):
            with self.subTest(paths=paths):
                result, show = self.invoke(paths, check)
                self.assertEqual(result, 2)
                show.assert_not_called()

    def test_missing_ui_dependency_returns_actionable_error(self):
        with (patch.object(cli, 'require_windows'),
              patch.object(cli, 'cursor_point', return_value=(2, 3)),
              patch.object(cli, 'inspect_file', return_value=FileCheck(True, True)),
              patch.object(cli, 'show_preview', side_effect=ImportError('PySide6')),
              redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as err):
            self.assertEqual(cli.main(['--gui', '--', r'C:\a.png']), 5)
        self.assertIn('pip install', err.getvalue())

    def test_gui_shortcut_has_own_identity_direct_pythonw_and_no_log_requirement(self):
        root = PureWindowsPath(r'C:\My project & æøå')
        exe = root / '.venv/Scripts/python.exe'
        gui, diagnostic = shortcut_plan(root, exe, 'gui'), shortcut_plan(root, exe)
        self.assertTrue(gui['target'].endswith('pythonw.exe'))
        self.assertIn(' --gui --', gui['arguments'])
        self.assertNotIn('--enable', gui['arguments'])
        self.assertNotEqual(gui['name'], diagnostic['name'])
        self.assertNotEqual(gui['description'], diagnostic['description'])
        self.assertTrue(diagnostic['target'].endswith('python.exe'))
        with self.assertRaises(ValueError):
            shortcut_plan(root, exe, 'unexpected')
