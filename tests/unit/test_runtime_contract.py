import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from filewheel.runtime import require_runtime


class RuntimeTests(unittest.TestCase):
    def test_only_application_python314_supported(self):
        for version in ((3, 12), (3, 15)):
            with patch('filewheel.runtime.sys.version_info', version), self.assertRaisesRegex(RuntimeError, '3.14'):
                require_runtime()
        with patch('filewheel.runtime.sys.version_info', (3, 14)):
            require_runtime()

    def test_one_complete_desktop_extra_and_python_constraint(self):
        config = tomllib.loads(Path('pyproject.toml').read_text())
        self.assertEqual(config['project']['requires-python'], '>=3.14,<3.15')
        desktop = config['project']['optional-dependencies']['desktop']
        for dependency in ('PySide6-Essentials', 'Pillow', 'PyMuPDF', 'pdf2docx', 'markitdown', 'pillow-heif', 'comtypes'):
            self.assertTrue(any(value.startswith(dependency) for value in desktop))
        self.assertNotIn("python_version <", str(desktop))
