"""Owned user desktop/Dolphin actions; no default MIME associations changed."""

import os
import tempfile
from pathlib import Path


def data_root():
    value = Path(os.getenv("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    return value if value.is_absolute() else Path.home() / ".local/share"


def quote(value):
    if any(character in value for character in ("\n", "\r", "\t")):
        raise ValueError("Desktop launcher paths cannot contain line breaks")
    for char in ("\\", '"', "`", "$"):
        value = value.replace(char, "\\" + char)
    return '"' + value.replace("\\", "\\\\").replace("%", "%%") + '"'


def entries(command):
    if not command or any(char in str(command[0]) for char in ("=", "%")):
        raise ValueError(
            "Desktop executable paths cannot contain = or % (desktop-parser limitation)"
        )
    executable = " ".join(quote(str(part)) for part in command)
    common = "X-Filewheel-Owned=true\n"
    desktop = (
        "[Desktop Entry]\nType=Application\nName=Filewheel\nComment=Local file converter\n"
        + common
        + "Exec="
        + executable
        + " --ui-backend quick -- %f\n"
        "Icon=filewheel\nTerminal=false\nCategories=Utility;\nMimeType=application/octet-stream;\n"
    )
    service = (
        "[Desktop Entry]\nType=Service\nName=Filewheel\nMimeType=application/octet-stream;\n"
        "Actions=Convert;\n" + common + "\n[Desktop Action Convert]\nName=Convert with Filewheel\n"
        "Icon=filewheel\nExec=" + executable + " --gui --ui-backend quick -- %f\n"
    )
    icon = '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><circle cx="32" cy="32" r="29" fill="#173e32" stroke="#c4ad72"/><text x="32" y="45" text-anchor="middle" font-size="38" fill="#f5efdf">F</text></svg>\n'
    root = data_root()
    return {
        root / "applications/org.filewheel.Filewheel.desktop": desktop,
        root / "kio/servicemenus/org.filewheel.Filewheel.desktop": service,
        root / "icons/hicolor/scalable/apps/filewheel.svg": icon,
    }


def atomic_write(path, content, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as output:
            temporary = Path(output.name)
            output.write(content)
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def configure(action, command):
    if action not in ("install", "remove"):
        raise ValueError("Unknown integration action")
    expected = entries(command)
    # Preflight every entry before mutating any, including the shared icon name.
    for path, content in expected.items():
        if path.is_symlink() or (
            path.exists() and (not path.is_file() or path.read_text() != content)
        ):
            raise RuntimeError(
                "Preserving an integration entry from another installation: " + str(path)
            )
    for path, content in expected.items():
        if action == "remove":
            path.unlink(missing_ok=True)
        else:
            atomic_write(path, content, 0o755 if "servicemenus" in path.parts else 0o644)
