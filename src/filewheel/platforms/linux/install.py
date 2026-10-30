"""Single-AppImage user installation; only owned bytes/entries can be replaced."""

import hashlib
import json
import os
import re
import stat
import tempfile
from pathlib import Path

from filewheel.platforms.linux.integration import atomic_write, configure, data_root


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def _paths():
    root = data_root() / "filewheel/app"
    if root.is_symlink() or root.parent.is_symlink():
        raise RuntimeError("Install directory must not be a symlink")
    return root, root / "Filewheel.AppImage", root / "installation.json"


def _manifest(path):
    if path.is_symlink() or path.stat().st_size > 4096:
        raise RuntimeError("Invalid installation manifest")
    value = json.loads(path.read_text())
    if (
        set(value) != {"schema", "sha256"}
        or value["schema"] != 1
        or not isinstance(value["sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is None
    ):
        raise RuntimeError("Invalid installation manifest")
    return value


def _owned(target, manifest):
    if target.is_symlink() or manifest.is_symlink():
        raise RuntimeError("Preserving a symlink in the install location")
    if not target.exists() and not manifest.exists():
        return
    if target.is_symlink() or not target.is_file() or not manifest.is_file():
        raise RuntimeError("Preserving an incomplete or unowned installation")
    if digest(target) != _manifest(manifest)["sha256"]:
        raise RuntimeError("Installed file differs from ownership manifest; preserving it")


def install(image):
    source = Path(image).resolve(strict=True)
    if not stat.S_ISREG(source.stat().st_mode):
        raise RuntimeError("Installer source must be a regular AppImage")
    with source.open("rb") as input_file:
        header = input_file.read(16)
    if header[:4] != b"\x7fELF" or header[8:11] not in (b"AI\x01", b"AI\x02"):
        raise RuntimeError("Run --install-user from a real AppImage")
    root, target, manifest = _paths()
    _owned(target, manifest)
    root.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with (
            source.open("rb") as input_file,
            tempfile.NamedTemporaryFile(dir=root, delete=False) as output,
        ):
            temporary = Path(output.name)
            for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
                output.write(chunk)
        temporary.chmod(0o755)
        checksum = digest(temporary)
        # Integration preflight refuses edits/unowned entries before binary replacement.
        from filewheel.platforms.linux.integration import preflight

        preflight([str(target)])
        os.replace(temporary, target)
        atomic_write(manifest, json.dumps({"schema": 1, "sha256": checksum}) + "\n", 0o600)
        configure("install", [str(target)])
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
    return target


def uninstall():
    root, target, manifest = _paths()
    _owned(target, manifest)
    if not manifest.exists():
        return
    configure("remove", [str(target)])
    # Preserve startup entries from another interpreter/installation.
    from filewheel.platforms.linux import startup

    if startup.is_enabled([str(target)]):
        startup.configure("remove", [str(target)])
    target.unlink()
    manifest.unlink()
    try:
        root.rmdir()
    except OSError:
        pass
