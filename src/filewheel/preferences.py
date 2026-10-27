"""Small per-user preferences, independent of Qt and startup registration."""
import json
import os
from pathlib import Path
import tempfile


def _path():
    return Path(os.environ['LOCALAPPDATA']) / 'Filewheel' / 'preferences.json'


def wheel_enabled():
    try:
        with _path().open('r', encoding='utf-8') as stream:
            value = json.loads(stream.read(4097))
        return value.get('wheel_enabled', True) is not False if isinstance(value, dict) else True
    except (OSError, ValueError, KeyError):
        return True


def save_wheel_enabled(enabled):
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='preferences-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump({'wheel_enabled': bool(enabled)}, stream)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
