import unittest
from pathlib import PureWindowsPath
from unittest.mock import patch

from filewheel.paths import application_root, launch_command
from filewheel.platforms.windows.sendto import shortcut_plan


class FrozenIntegrationTests(unittest.TestCase):
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
              patch('filewheel.paths.sys.executable', '/tmp/Filewheel/Filewheel.exe'),
              patch('filewheel.paths.sys._MEIPASS', '/tmp/Filewheel/_internal', create=True)):
            self.assertEqual(str(application_root()), '/tmp/Filewheel')
            self.assertEqual(launch_command('--tray'), ['/tmp/Filewheel/Filewheel.exe','--tray'])
