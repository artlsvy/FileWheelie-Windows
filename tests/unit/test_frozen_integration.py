import unittest
from pathlib import Path, PureWindowsPath
from unittest.mock import patch

from filewheel.paths import application_root, bundled_tool_root, launch_command
from filewheel.platforms.windows.sendto import shortcut_plan


class FrozenIntegrationTests(unittest.TestCase):
    def test_onefile_tools_use_extraction_but_shortcuts_use_real_exe(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            extracted = root / 'unpacked'
            (extracted / 'tools').mkdir(parents=True)
            with (patch('filewheel.paths.sys.frozen', True, create=True),
                  patch('filewheel.paths.sys._MEIPASS', str(extracted), create=True),
                  patch('filewheel.paths.sys.executable', str(root / 'Filewheel.exe'))):
                self.assertEqual(bundled_tool_root(), extracted)
                self.assertEqual(application_root(), root)
                self.assertEqual(launch_command('--tray'), [str(root / 'Filewheel.exe'), '--tray'])

    def test_frozen_executable_never_receives_python_module_arguments(self):
        root = PureWindowsPath('C:/Filewheel personal')
        for mode in ('gui','diagnostic'):
            plan = shortcut_plan(root, root/'Filewheel.exe', mode, frozen=True)
            self.assertEqual(plan['target'], str(root/'Filewheel.exe'))
            self.assertNotIn('-m', plan['arguments'])
            self.assertNotIn('python', plan['target'].lower())
            self.assertTrue(plan['arguments'].endswith('--'))

    def test_development_gui_uses_main_application_for_instance_routing(self):
        plan = shortcut_plan(PureWindowsPath('C:/repo'), PureWindowsPath('C:/repo/python.exe'), 'gui')
        self.assertEqual(plan['arguments'], '-m filewheel --gui --')
        self.assertEqual(plan['previous_arguments'], ['-m filewheel.platforms.windows.explicit_path_diagnostics --gui --'])

    def test_application_root_is_executable_sibling_not_internal(self):
        with (patch('filewheel.paths.sys.frozen', True, create=True),
              patch('filewheel.paths.sys.executable', 'C:/Filewheel/Filewheel.exe'),
              patch('filewheel.paths.sys._MEIPASS', 'C:/Filewheel/_internal', create=True)):
            self.assertEqual(application_root(), Path('C:/Filewheel'))
            self.assertEqual(launch_command('--tray'), ['C:/Filewheel/Filewheel.exe','--tray'])
