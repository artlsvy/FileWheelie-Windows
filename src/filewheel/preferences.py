"""Small per-user preferences, independent of Qt and startup registration."""
import json
import os
import tempfile
from pathlib import Path

from filewheel.ui.theme import normalize_accent


def _path():
    return Path(os.environ['LOCALAPPDATA']) / 'Filewheel' / 'preferences.json'


def _read():
    try:
        with _path().open('r', encoding='utf-8') as stream:
            value = json.loads(stream.read(4097))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, KeyError):
        return {}


def wheel_enabled():
    return _read().get('wheel_enabled', True) is not False


def accent_color():
    try:
        return normalize_accent(_read().get('accent_color'))
    except ValueError:
        return None


def save_wheel_enabled(enabled):
    _save('wheel_enabled', bool(enabled))


def save_accent_color(color):
    _save('accent_color', normalize_accent(color))


def _save(key, value):
    path = _path()
    settings = _read()
    if value is None:
        settings.pop(key, None)
    else:
        settings[key] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='preferences-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(settings, stream)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
