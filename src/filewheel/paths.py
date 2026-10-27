"""Frozen executable siblings and package resources have different roots."""
import sys
from pathlib import Path


def application_root():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def launch_command(*arguments):
    if getattr(sys, 'frozen', False):
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
