"""Flatten known CI artifacts, rejecting ambiguous names and generating checksums."""

import hashlib
import shutil
from pathlib import Path


def assemble(root, output):
    files = {}
    for platform, name, destination in (
        ("linux", "Filewheel-Linux-x86_64.AppImage", "Filewheel-Linux-x86_64.AppImage"),
        ("linux", "BUILD-INFO.json", "LINUX-BUILD-INFO.json"),
        ("windows", "FilewheelSetup.exe", "FilewheelSetup.exe"),
        ("windows", "INSTALLER-BUILD-INFO.json", "WINDOWS-BUILD-INFO.json"),
    ):
        matches = list((root / platform).rglob(name))
        if len(matches) != 1 or not matches[0].is_file() or matches[0].is_symlink():
            raise ValueError("Missing or ambiguous CI artifact: " + name)
        files[destination] = matches[0]
    output.mkdir(exist_ok=False)
    for destination, source in files.items():
        shutil.copyfile(source, output / destination)
    sums = []
    for name in ("Filewheel-Linux-x86_64.AppImage", "FilewheelSetup.exe"):
        with (output / name).open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        sums.append(digest + "  " + name)
    (output / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n")


if __name__ == "__main__":
    assemble(Path("artifacts"), Path("release"))
