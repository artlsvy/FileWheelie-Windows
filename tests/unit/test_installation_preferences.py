"""Future checks for persisted wheel choice and reused dependency selection."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from filewheel import preferences
from filewheel.installation import selected_tool


class InstallationPreferencesTests(unittest.TestCase):
    def test_wheel_defaults_on_and_persists_off_then_on(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'LOCALAPPDATA': directory}):
            self.assertTrue(preferences.wheel_enabled())
            preferences.save_wheel_enabled(False)
            self.assertFalse(preferences.wheel_enabled())
            preferences.save_wheel_enabled(True)
            self.assertTrue(preferences.wheel_enabled())
            (Path(directory) / 'Filewheel/preferences.json').write_text('{bad', encoding='utf-8')
            self.assertTrue(preferences.wheel_enabled())

    def test_selected_unicode_tool_is_used_only_outside_strict_portable_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tool = root / 'tools é/pandoc.exe'
            tool.parent.mkdir()
            tool.write_bytes(b'placeholder')
            (root / 'installation.ini').write_text(
                '[Dependencies]\nPandocPath=' + str(tool) + '\n', encoding='utf-8-sig')
            with (patch('filewheel.installation.application_root', return_value=root),
                  patch.dict(os.environ, {'FILEWHEEL_BUNDLED_TOOLS_ONLY': '0'})):
                self.assertEqual(selected_tool('Pandoc'), tool)
                with patch.dict(os.environ, {'FILEWHEEL_BUNDLED_TOOLS_ONLY': '1'}):
                    self.assertIsNone(selected_tool('Pandoc'))
            tool.unlink()
            with patch('filewheel.installation.application_root', return_value=root):
                self.assertIsNone(selected_tool('Pandoc'))
