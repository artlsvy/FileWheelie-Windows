"""Paths selected by per-user Setup; portable builds keep embedded tools."""
from configparser import ConfigParser, Error
import os
from pathlib import Path

from filewheel.paths import application_root


def selected_tool(name):
    if os.environ.get('FILEWHEEL_BUNDLED_TOOLS_ONLY') == '1':
        return None
    try:
        path = application_root() / 'installation.ini'
        if path.stat().st_size > 16384:
            return None
        parser = ConfigParser(interpolation=None)
        parser.read(path, encoding='utf-8-sig')
        value = parser.get('Dependencies', name + 'Path', fallback='')
        candidate = Path(value)
        if value and candidate.is_absolute() and candidate.is_file():
            return candidate
    except (OSError, ValueError, Error):
        pass
    return None
