"""Assemble complete baseline-container native tools and their non-core ELF deps.

Run only inside the Linux build container, against trusted apt/hashed inputs.
"""

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path


def elf(path):
    try:
        with path.open("rb") as stream:
            return stream.read(4) == b"\x7fELF"
    except OSError:
        return False


def main():
    distribution = Path(sys.argv[1]).resolve(strict=True)
    tools = distribution / "tools"
    tools.mkdir(exist_ok=False)
    libraries = tools / "native-libs"
    libraries.mkdir()
    office = tools / "libreoffice"

    # Ubuntu ships two optional LDAP sample links without their sample targets.
    # Ignore only those known dangling examples; missing runtime files still fail.
    def ignore_samples(directory, names):
        return [
            name
            for name in names
            if name in {"oo-ldap.xcd.sample", "oo-ad-ldap.xcd.sample"}
            and (Path(directory) / name).is_symlink()
            and not (Path(directory) / name).exists()
        ]

    shutil.copytree("/usr/lib/libreoffice", office, symlinks=False, ignore=ignore_samples)
    # Ubuntu's FHS bootstrap files have absolute system installation paths.
    # All registry data above has been dereferenced into this private tree.
    fundamental = office / "program/fundamentalrc"
    config = fundamental.read_text()
    if "BRAND_BASE_DIR=file:///usr/lib/libreoffice" not in config:
        raise RuntimeError("Review changed LibreOffice bootstrap layout before bundling")
    fundamental.write_text(
        config.replace("file:///usr/lib/libreoffice", "${ORIGIN}/..")
        .replace("file:///etc/libreoffice/registry", "${BRAND_BASE_DIR}/share/registry")
        .replace(
            "URE_MORE_JAVA_CLASSPATH_URLS= file:///usr/share/java/hsqldb1.8.0.jar",
            "URE_MORE_JAVA_CLASSPATH_URLS=",
        )
    )
    (office / "program/sofficerc").write_text("[Bootstrap]\nLogo=0\nNativeProgress=0\n")
    # NSS loads these at runtime. ldd alone misses them; PDF export needs softokn.
    nss = Path("/usr/lib/x86_64-linux-gnu/nss")
    for name in ("libsoftokn3.so", "libfreebl3.so", "libfreeblpriv3.so", "libnssckbi.so"):
        shutil.copyfile(nss / name, libraries / name)
    shutil.copyfile("/usr/share/doc/libreoffice-common/copyright", office / "LICENSE.debian")
    ffmpeg = tools / "ffmpeg"
    ffmpeg.mkdir()
    shutil.copyfile("/usr/bin/ffmpeg", ffmpeg / "ffmpeg.real")
    (ffmpeg / "ffmpeg.real").chmod(0o755)
    shutil.copyfile("/usr/share/doc/ffmpeg/copyright", ffmpeg / "LICENSE.debian")
    data = Path("/tmp/pandoc.tar.gz").read_bytes()
    expected = json.loads(Path("packaging/pandoc-artifacts.json").read_text())["artifacts"][
        "linux-amd64"
    ]["sha256"]
    if hashlib.sha256(data).hexdigest() != expected:
        raise RuntimeError("Pandoc archive hash mismatch")
    with tarfile.open("/tmp/pandoc.tar.gz") as archive:
        archive.extractall("/tmp/pandoc-unpacked", filter="data")
    source = Path("/tmp/pandoc-unpacked/pandoc-3.12.1")
    pandoc = tools / "pandoc"
    pandoc.mkdir()
    shutil.copyfile(source / "bin/pandoc", pandoc / "pandoc.real")
    (pandoc / "pandoc.real").chmod(0o755)
    for path in source.rglob("*"):
        if path.is_file() and path.name.lower().startswith(("copying", "copyright", "license")):
            shutil.copyfile(path, pandoc / path.name)
    # Preserve all upstream documentation/notices in the outer tools tree too.
    shutil.copytree(source / "share", tools / "pandoc-share")
    for notice in Path("packaging/linux/notices/pandoc-3.12.1").iterdir():
        shutil.copyfile(notice, pandoc / notice.name)
    if not any(p.name.startswith("COPY") for p in pandoc.iterdir()):
        raise RuntimeError("Pandoc license notices were not found")
    excluded = re.compile(
        r"^(ld-linux.*|libc\.so.*|libm\.so.*|libmvec\.so.*|libpthread\.so.*|libdl\.so.*|librt\.so.*|libresolv\.so.*)$"
    )
    pending = [p for p in tools.rglob("*") if p.is_file() and elf(p)]
    seen = set()
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        listing = subprocess.run(["ldd", str(path)], capture_output=True, text=True, check=False)
        if "not found" in listing.stdout:
            raise RuntimeError("Unresolved native dependency: " + str(path))
        for name, value in re.findall(r"^\s*(\S+)\s+=>\s+(/\S+)", listing.stdout, re.MULTILINE):
            source_lib = Path(value)
            if excluded.match(name) or source_lib.is_relative_to(tools):
                continue
            destination = libraries / name
            if not destination.exists():
                shutil.copyfile(source_lib.resolve(), destination)
                pending.append(destination)
    # Each external tool has its own trusted loader environment, separate from Qt.
    for wrapper, real, relative in (
        (ffmpeg / "ffmpeg", "ffmpeg.real", "../native-libs"),
        (pandoc / "pandoc", "pandoc.real", "../native-libs"),
        (office / "program/soffice", "soffice.upstream", "../../native-libs"),
    ):
        if wrapper.exists():
            wrapper.rename(wrapper.with_name(real))
        launch = "oosplash" if wrapper == office / "program/soffice" else real
        wrapper.write_text(
            '#!/bin/sh\nHERE=$(CDPATH= cd -- "${0%/*}" && pwd -P)\n'
            'export LD_LIBRARY_PATH="$HERE:$HERE/' + relative + '"\n'
            'exec "$HERE/' + launch + '" "$@"\n'
        )
        wrapper.chmod(0o755)
    notices = tools / "distribution-notices"
    notices.mkdir()
    for notice in Path("/usr/share/doc").glob("*/copyright"):
        if notice.is_file():
            shutil.copyfile(notice, notices / (notice.parent.name + ".copyright"))
    manifest = {}
    for package in (
        "ffmpeg",
        "libreoffice-core",
        "libreoffice-writer",
        "libreoffice-calc",
        "libreoffice-impress",
    ):
        manifest[package] = subprocess.check_output(
            ["dpkg-query", "-W", "-f=${Version}", package], text=True
        )
    (tools / "BUILD-INFO.json").write_text(
        json.dumps({"apt_versions": manifest, "pandoc": "3.12.1"}, indent=2) + "\n"
    )
    print("Bundled ELF dependencies:", len(seen))


if __name__ == "__main__":
    main()
