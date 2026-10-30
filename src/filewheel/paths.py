"""Frozen executable siblings and package resources have different roots."""
import os
import sys
from pathlib import Path


def application_root():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def bundled_tool_root():
    """Embedded onefile resources differ from the stable shortcut/EXE folder."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        extracted = Path(sys._MEIPASS)
        if (extracted / 'tools').is_dir():
            return extracted
    return application_root()


def launch_command(*arguments):
    if getattr(sys, 'frozen', False):
        if sys.platform == 'linux' and os.getenv('APPIMAGE'):
            image=Path(os.environ['APPIMAGE']).resolve(strict=True)
            if not image.is_file():
                raise RuntimeError('AppImage launch path is unavailable')
            return [str(image), *arguments]
        return [sys.executable, *arguments]
    python = Path(sys.executable)
    if sys.platform == 'win32' and python.name.lower() == 'python.exe':
        python = python.with_name('pythonw.exe')
    return [str(python), '-m', 'filewheel', *arguments]


def ensure_separate_tool_source(source, output):
    """Resolve filesystem aliases before a build may replace its own output."""
    source = Path(source).resolve(strict=True)
    output = Path(output).resolve()
    if source == output or source.is_relative_to(output) or output.is_relative_to(source):
        raise ValueError('Tool physical source and build output must not overlap')
    return source
