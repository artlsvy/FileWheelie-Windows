"""Record build environment/source without importing Filewheel engines or UI."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def git_value(root, *arguments):
    git = shutil.which("git")
    if git is None:
        return None
    result = subprocess.run(
        [git, "-C", str(root), *arguments], capture_output=True, text=True, timeout=15, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    lock = root / "packaging/windows-py314.lock"
    versions = {
        distribution.metadata["Name"]: distribution.version
        for distribution in importlib.metadata.distributions()
    }
    manifest = {
        "schema_version": 1,
        "application": "Filewheel",
        "created_utc": datetime.now(UTC).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "source_revision": git_value(root, "rev-parse", "HEAD"),
        "source_status": git_value(root, "status", "--porcelain"),
        "lock_sha256": hashlib.sha256(lock.read_bytes()).hexdigest(),
        "distributions": dict(sorted(versions.items(), key=lambda pair: pair[0].lower())),
        "layout": "onedir",
        "experimental_mouse3_default": False,
    }
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
