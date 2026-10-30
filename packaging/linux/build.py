"""Rebuild baseline Linux payload and assemble AppImage/DEB without host installs."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "build-tools/linux"


def sha(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def run(command, **kwargs):
    return subprocess.run(command, check=True, **kwargs)


def fetch(metadata, filename):
    """Only build-time pinned downloads; never run a mismatched artifact."""
    target = CACHE / filename
    if not target.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=CACHE, delete=False) as stream:
            temporary = Path(stream.name)
            try:
                with urlopen(metadata["url"], timeout=60) as remote:
                    shutil.copyfileobj(remote, stream)
                stream.flush()
                if sha(temporary) != metadata["sha256"]:
                    raise RuntimeError("Download checksum mismatch: " + filename)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
    if sha(target) != metadata["sha256"]:
        raise RuntimeError("Cached checksum mismatch: " + str(target))
    return target


def audit(directory):
    """Record the highest required GLIBC symbol in every shipped ELF, not host ldd."""
    requirements = {}
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        with path.open("rb") as stream:
            if stream.read(4) != b"\x7fELF":
                continue
        result = run(["readelf", "--version-info", str(path)], capture_output=True, text=True)
        versions = {
            tuple(map(int, version.split(".")))
            for version in re.findall(r"Name: GLIBC_([0-9.]+)", result.stdout)
        }
        if versions:
            requirements[str(path.relative_to(directory))] = ".".join(map(str, max(versions)))
    return requirements


def icon():
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
        '<circle cx="32" cy="32" r="29" fill="#173e32" stroke="#c4ad72"/>'
        '<text x="32" y="45" text-anchor="middle" font-size="38" fill="#f5efdf">F</text></svg>\n'
    )


def desktop(exec_value):
    return (
        "[Desktop Entry]\nType=Application\nName=Filewheel\n"
        "Comment=Local file converter — Linux preview\nExec="
        + exec_value
        + " --ui-backend quick -- %f\nIcon=filewheel\nTerminal=false\n"
        "Categories=Utility;\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New, nonexistent output folder")
    parser.add_argument("--image", default="filewheel-linux-frozen:py314")
    parser.add_argument(
        "--skip-freeze", action="store_true", help="Reuse explicitly named Docker image"
    )
    parser.add_argument("--deb", action="store_true")
    parser.add_argument(
        "--private-dolphin-prefix",
        type=Path,
        help="Optional exact-version isolated prefix; reduces platform compatibility",
    )
    args = parser.parse_args()
    os.chdir(ROOT)
    if args.deb and args.private_dolphin_prefix:
        parser.error("Build the broad core DEB separately from the exact-version Dolphin preview")
    if args.output.exists():
        raise SystemExit("Refusing to replace output directory: " + str(args.output))
    pins = json.loads((ROOT / "packaging/linux/artifacts.json").read_text())
    fetch(pins["python"], "Python-3.14.10.tar.xz")
    pandoc = json.loads((ROOT / "packaging/pandoc-artifacts.json").read_text())["artifacts"][
        "linux-amd64"
    ]
    fetch(pandoc, "pandoc-linux.tar.gz")
    image_tool = fetch(pins["appimagetool"], "appimagetool-x86_64.AppImage")
    runtime = fetch(pins["runtime"], "runtime-x86_64")
    image_tool.chmod(0o755)
    for name, meta in pins["pandoc_notices"].items():
        if sha(ROOT / "packaging/linux/notices/pandoc-3.12.1" / name) != meta["sha256"]:
            raise RuntimeError("Pandoc notice checksum mismatch")
    if not args.skip_freeze:
        run(
            [
                "docker",
                "build",
                "--progress",
                "plain",
                "-f",
                "packaging/linux/Dockerfile",
                "-t",
                args.image,
                ".",
            ]
        )
    # A reused freeze must contain the current application source. Packaging
    # scripts can evolve without silently labelling an old app as the new one.
    source_check = """import hashlib,json
from pathlib import Path
root=Path('/work')
files=[p for p in (root/'src').rglob('*') if p.is_file() and p.suffix in {'.py','.qml','.ps1'}]
files += [root/'packaging/entry.py',root/'packaging/runtime_hook.py']
print(json.dumps({str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}))
"""
    expected = json.loads(
        subprocess.check_output(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                args.image,
                "python3.14",
                "-c",
                source_check,
            ],
            text=True,
        )
    )
    current_files = [
        p for p in (ROOT / "src").rglob("*") if p.is_file() and p.suffix in {".py", ".qml", ".ps1"}
    ]
    current_files += [ROOT / "packaging/entry.py", ROOT / "packaging/runtime_hook.py"]
    current = {str(p.relative_to(ROOT)): sha(p) for p in current_files}
    if current != expected:
        raise RuntimeError("Frozen source differs; rebuild without --skip-freeze")
    output = args.output.resolve()
    output.mkdir(parents=True)
    appdir = output / "AppDir"
    payload = appdir / "usr/lib/filewheel"
    payload.parent.mkdir(parents=True)
    container = subprocess.check_output(["docker", "create", args.image], text=True).strip()
    try:
        run(["docker", "cp", container + ":/work/dist/Filewheel", str(payload)])
        run(
            [
                "docker",
                "cp",
                container + ":/tmp/Python-3.14.10/LICENSE",
                str(payload / "PYTHON-LICENSE.txt"),
            ]
        )
        run(
            [
                "docker",
                "cp",
                container + ":/usr/share/fonts/truetype/liberation2/.",
                str(payload / "tools/libreoffice/share/fonts/truetype"),
            ]
        )
        run(["docker", "cp", container + ":/tmp/frozen-smoke", str(output / "frozen-smoke")])
    finally:
        run(["docker", "rm", container], stdout=subprocess.DEVNULL)
    if args.private_dolphin_prefix:
        prefix = args.private_dolphin_prefix.resolve(strict=True)
        if not (prefix / "bin/dolphin").is_file():
            raise RuntimeError("Expected complete private Dolphin prefix")
        shutil.copytree(prefix, payload / "tools/dolphin", symlinks=True)
    # PyInstaller's automatic dependency scan can retain libmvec, a member of
    # the host glibc family. Never ship it against a different host libc/libm.
    for path in payload.rglob("libmvec.so*"):
        path.unlink()
    requirements = audit(payload)
    baseline = {
        name: value for name, value in requirements.items() if not name.startswith("tools/dolphin/")
    }
    (output / "elf-requirements.json").write_text(json.dumps(requirements, indent=2) + "\n")
    if any(tuple(map(int, value.split("."))) > (2, 35) for value in baseline.values()):
        raise RuntimeError("Core payload exceeds GLIBC 2.35 baseline; inspect audit")
    launcher = appdir / "AppRun"
    launcher.write_text(
        '#!/bin/sh\nHERE=$(CDPATH= cd -- "${0%/*}" && pwd -P)\n'
        'exec "$HERE/usr/lib/filewheel/filewheel" "$@"\n'
    )
    launcher.chmod(0o755)
    (appdir / "filewheel.desktop").write_text(desktop("filewheel"))
    (appdir / "filewheel.svg").write_text(icon())
    os.symlink("filewheel.svg", appdir / ".DirIcon")
    # Include the actual source snapshot for this preview, plus the bridge patch.
    files = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
    # Capture new implementation files without sweeping unrelated user assets
    # into a distributable source archive merely because they are untracked.
    new_files = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard"], text=True
    ).splitlines()
    files += [
        name
        for name in new_files
        if Path(name).parts[0]
        in {
            "src",
            "packaging",
            "scripts",
            "tests",
            "prototypes",
            "linux-evidence",
        }
    ]
    source = payload / "FILEWHEEL-SOURCE.tar.gz"
    with tarfile.open(source, "w:gz") as archive:
        for name in files:
            path = ROOT / name
            if path.is_file() and not path.is_relative_to(output):
                archive.add(path, arcname="filewheel/" + name, recursive=False)
    variant = "kubuntu2604-private-dolphin" if args.private_dolphin_prefix else "linux"
    target = output / ("Filewheel-0.3-linux-preview-" + variant + "-x86_64.AppImage")
    env = dict(os.environ, ARCH="x86_64")
    run(
        [
            str(image_tool),
            "--appimage-extract-and-run",
            "--runtime-file",
            str(runtime),
            "--no-appstream",
            "--comp",
            "zstd",
            "--mksquashfs-opt=-processors",
            "--mksquashfs-opt=2",
            str(appdir),
            str(target),
        ],
        env=env,
    )
    target.chmod(0o755)
    if args.deb:
        package = output / "deb-root"
        installed = package / "opt/filewheel"
        installed.parent.mkdir(parents=True)
        shutil.copytree(payload, installed, symlinks=True)
        control = package / "DEBIAN"
        control.mkdir()
        (control / "control").write_text(
            "Package: filewheel\nVersion: 0.3.0~linux1\nArchitecture: amd64\n"
            "Maintainer: Filewheel contributors\nSection: utils\nPriority: optional\n"
            "Depends: libc6 (>= 2.35), libgl1, libegl1, libdbus-1-3, libfontconfig1, "
            "libxkbcommon0, libwayland-client0\n"
            "Description: Local radial file converter (Linux preview)\n"
            " Python, Qt and converter tools included; optional private Dolphin is version-specific.\n"
        )
        applications = package / "usr/share/applications"
        applications.mkdir(parents=True)
        (applications / "org.filewheel.Filewheel.desktop").write_text(
            desktop("/opt/filewheel/filewheel")
        )
        services = package / "usr/share/kio/servicemenus"
        services.mkdir(parents=True)
        service = services / "org.filewheel.Filewheel.desktop"
        service.write_text(
            "[Desktop Entry]\nType=Service\nMimeType=application/octet-stream;\n"
            "Actions=Convert;\nX-KDE-RequiredNumberOfUrls=1\n\n"
            "[Desktop Action Convert]\nName=Convert with Filewheel\nIcon=filewheel\n"
            "Exec=/opt/filewheel/filewheel --gui --ui-backend quick -- %f\n"
        )
        service.chmod(0o755)
        icons = package / "usr/share/icons/hicolor/scalable/apps"
        icons.mkdir(parents=True)
        (icons / "filewheel.svg").write_text(icon())
        run(
            [
                "dpkg-deb",
                "--threads-max=2",
                "-Zgzip",
                "--root-owner-group",
                "--build",
                str(package),
                str(output / "filewheel_0.3.0~linux1_amd64.deb"),
            ]
        )
    # Test the final container, not just its unfrozen source or pre-assembly tree.
    smoke = output / "appimage-smoke"
    environment = dict(
        os.environ,
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        FILEWHEEL_LOG_DIR=str(smoke),
    )
    with (output / "appimage-smoke.log").open("w") as log:
        run(
            [str(target), "--appimage-extract-and-run", "--self-test", "--ui-backend", "quick"],
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    run(["python3", str(ROOT / "packaging/linux/verify_smoke.py"), str(smoke / "self-test.json")])
    artifacts = {
        path.name: sha(path) for path in output.iterdir() if path.suffix in {".AppImage", ".deb"}
    }
    image_id = subprocess.check_output(
        ["docker", "image", "inspect", "--format={{.Id}}", args.image], text=True
    ).strip()
    (output / "BUILD-INFO.json").write_text(
        json.dumps(
            {
                "source_head": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], text=True
                ).strip(),
                "source_dirty": bool(
                    subprocess.check_output(["git", "status", "--porcelain"], text=True)
                ),
                "docker_image": image_id,
                "glibc_core_floor": max(
                    baseline.values(), key=lambda value: tuple(map(int, value.split(".")))
                ),
                "private_dolphin": bool(args.private_dolphin_prefix),
                "artifacts": artifacts,
                "dependency_lock_sha256": sha(ROOT / "packaging/linux/python-py314-x86_64.lock"),
                "source_snapshot_sha256": sha(source),
                "bit_reproducible": False,
            },
            indent=2,
        )
        + "\n"
    )
    print("Artifacts:", output)


if __name__ == "__main__":
    main()
