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
