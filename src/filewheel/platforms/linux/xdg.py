"""Per-user state locations, without creating folders at import time."""

import os
from pathlib import Path


def _directory(variable, fallback):
    value = Path(os.environ.get(variable, fallback))
    return (value if value.is_absolute() else Path(fallback)) / "filewheel"


def config_root():
    return _directory("XDG_CONFIG_HOME", str(Path.home() / ".config"))


def state_root():
    return _directory("XDG_STATE_HOME", str(Path.home() / ".local/state"))
