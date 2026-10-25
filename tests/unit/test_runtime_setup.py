"""The normal environment is one complete supported Python runtime."""
import unittest
from pathlib import Path
from unittest.mock import patch

from filewheel.runtime import require_runtime


class RuntimeSetupTests(unittest.TestCase):
    def test_wrong_runtime_has_actionable_message(self):
        with patch('filewheel.runtime.sys.version_info', (3, 15)), self.assertRaisesRegex(RuntimeError, 'py -3.14'):
            require_runtime()

    def test_setup_does_not_replace_existing_venv(self):
        text = Path('scripts/setup-windows.ps1').read_text()
        self.assertIn("if (-not (Test-Path -LiteralPath $Environment))", text)
        self.assertIn("sys.version_info[:2] == (3,14)", text)
        self.assertIn("'.[desktop]'", text)
        self.assertNotIn('Remove-Item', text)
