import unittest
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

from filewheel.platforms.windows.startup import configure, is_enabled


class StartupTests(unittest.TestCase):
    def fake(self, values):
        def query(key, name):
            if name not in values:
                raise FileNotFoundError
            return values[name]
        return SimpleNamespace(HKEY_CURRENT_USER=1, KEY_READ=2, KEY_SET_VALUE=3, REG_SZ=4,
                               OpenKey=lambda *args: nullcontext(1),
                               CreateKeyEx=lambda *args: nullcontext(1), QueryValueEx=query,
                               SetValueEx=lambda key,name,reserved,kind,value: values.update({name:(value,kind)}),
                               DeleteValue=lambda key,name: values.pop(name))

    def test_explicit_install_remove_owned_entry_with_experiment_off(self):
        values = {}
        with (patch.dict('sys.modules', {'winreg': self.fake(values)}),
              patch('filewheel.platforms.windows.startup.require_windows'),
              patch('filewheel.platforms.windows.startup.launch_command', return_value=['C:/Filewheel.exe','--tray'])):
            configure('install'); configure('install')
            self.assertIn('--tray', values['Filewheel'][0])
            self.assertNotIn('experimental', values['Filewheel'][0])
            configure('remove'); configure('remove')
        self.assertEqual(values, {})

    def test_foreign_entry_is_preserved(self):
        values = {'Filewheel':('other program',4)}
        with (patch.dict('sys.modules', {'winreg': self.fake(values)}),
              patch('filewheel.platforms.windows.startup.require_windows')):
            for action in ('install','remove'):
                with self.assertRaisesRegex(RuntimeError, 'differs'):
                    configure(action)
        self.assertEqual(values, {'Filewheel':('other program',4)})

    def test_installer_quoted_command_is_owned_and_removable(self):
        values = {'Filewheel': ('"C:/Filewheel.exe" --tray', 4)}
        with (patch.dict('sys.modules', {'winreg': self.fake(values)}),
              patch('filewheel.platforms.windows.startup.require_windows'),
              patch('filewheel.platforms.windows.startup.launch_command',
                    return_value=['C:/Filewheel.exe', '--tray'])):
            self.assertTrue(is_enabled())
            configure('remove')
            self.assertFalse(is_enabled())

    def test_foreign_non_string_entry_is_preserved(self):
        values = {'Filewheel': (['other', 'program'], 7)}
        with (patch.dict('sys.modules', {'winreg': self.fake(values)}),
              patch('filewheel.platforms.windows.startup.require_windows')):
            self.assertFalse(is_enabled())
            with self.assertRaisesRegex(RuntimeError, 'differs'):
                configure('install')
        self.assertEqual(values['Filewheel'], (['other', 'program'], 7))
