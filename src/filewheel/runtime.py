"""One supported application/build runtime; cleanup tools remain importable."""
import sys


def require_runtime():
    if sys.version_info[:2] != (3, 14):
        raise RuntimeError('Filewheel requires Python 3.14. Use py -3.14 to create .venv-filewheel.')
