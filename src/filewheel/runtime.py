"""One supported application/build runtime; cleanup tools remain importable."""
import sys


def require_runtime():
    if sys.version_info[:2] != (3, 14):
        raise RuntimeError('Filewheel requires Python 3.14. Use py -3.14 to create .venv-filewheel.')
    if sys.platform not in ('win32', 'linux'):
        raise RuntimeError('Filewheel supports Windows 11 or Linux.')
