"""Owned XDG login entry. No system-wide changes or shell command evaluation."""

import os
import tempfile

from filewheel.paths import launch_command
from filewheel.platforms.linux.integration import quote
from filewheel.platforms.linux.xdg import config_root


def _entry():
    return config_root().parent / "autostart/org.filewheel.Filewheel.desktop"


def _content():
    return (
        "[Desktop Entry]\nType=Application\nName=Filewheel\n"
        "X-Filewheel-Owned=true\nExec="
        + " ".join(map(quote, launch_command("--tray", "--ui-backend", "quick")))
        + "\n"
    )


def is_enabled():
    path = _entry()
    return path.is_file() and not path.is_symlink() and path.read_text() == _content()


def configure(action):
    if action not in ("install", "remove"):
        raise ValueError("Unknown startup action")
    path = _entry()
    if path.is_symlink() or (path.exists() and not is_enabled()):
        raise RuntimeError("Preserving startup entry owned by another installation")
    if action == "remove":
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as output:
            temporary = output.name
            output.write(_content())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
