"""Complete portable LibreOffice discovery and safe frozen external-tool launch."""

import argparse
import ctypes
import json
import ntpath
import os
import shutil
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from filewheel.paths import application_root, ensure_separate_tool_source

_DLL_LOCK = Lock()


@dataclass(frozen=True)
class LibreOfficeLocation:
    executable: Path
    source: str
    root: Path
    layout: str


def _nonempty_file(path):
    return path.is_file() and path.stat().st_size > 0


def _populated_directory(path):
    return path.is_dir() and next(path.iterdir(), None) is not None


def validate_bundle(root: Path, *, platform: str | None = None) -> LibreOfficeLocation:
    """Validate a complete flat/PortableApps tree, not a lone renamed launcher.

    This is structural validation, not certification of every vendor DLL. Native
    self-test and DOCX→PDF still establish whether a supplied build actually runs.
    """
    platform = sys.platform if platform is None else platform
    root = Path(root).resolve(strict=True)
    failures = []
    for layout, installation in (("flat", root), ("portableapps", root / "App/libreoffice")):
        program = installation / "program"
        names = ("soffice.com", "soffice.exe") if platform == "win32" else ("soffice",)
        executable = next(
            (program / name for name in names if _nonempty_file(program / name)), None
        )
        if executable is None:
            continue
        bootstrap = program / ("bootstrap.ini" if platform == "win32" else "bootstraprc")
        fundamental = program / ("fundamental.ini" if platform == "win32" else "fundamentalrc")
        libraries = tuple(program.glob("*.dll" if platform == "win32" else "*.so"))
        license_files = [
            path
            for path in installation.iterdir()
            if path.name.lower().startswith(("license", "copying", "notice"))
        ]
        services = (program / "services.rdb", program / "services/services.rdb")
        if (
            not _nonempty_file(program / "soffice.bin")
            or not _nonempty_file(bootstrap)
            or not _nonempty_file(fundamental)
            or not _nonempty_file(program / "types.rdb")
            or not any(_nonempty_file(path) for path in services)
            or not any(_nonempty_file(path) for path in libraries)
            or not _populated_directory(installation / "share/registry")
            or not (
                _populated_directory(program / "resource")
                or _populated_directory(installation / "share/config")
            )
            or not any(_nonempty_file(path) for path in license_files)
        ):
            failures.append(
                f"{layout} LibreOffice tree is incomplete: keep program, share, configs, libraries and licenses together"
            )
            continue
        if platform != "win32" and not os.access(executable, os.X_OK):
            failures.append(f"{layout} LibreOffice launcher is not executable")
            continue
        return LibreOfficeLocation(executable, "bundled", installation, layout)
    raise ValueError(
        "; ".join(failures) or "No complete flat or PortableApps LibreOffice installation was found"
    )


def _system_location(platform, excluded_root):
    excluded_root = excluded_root.resolve()

    def excluded(path):
        return path.resolve().is_relative_to(excluded_root)

    names = (
        ("soffice.com", "libreoffice", "soffice")
        if platform == "win32"
        else ("libreoffice", "soffice")
    )
    for name in names:
        candidate = shutil.which(name)
        if candidate:
            path = Path(candidate)
            if not excluded(path):
                return LibreOfficeLocation(path, "system", path.parent.parent, "system")
    if platform == "win32":
        for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
            root = os.environ.get(variable)
            if root:
                for name in ("soffice.com", "soffice.exe"):
                    path = Path(root) / "LibreOffice/program" / name
                    if _nonempty_file(path) and not excluded(path):
                        return LibreOfficeLocation(path, "system", path.parent.parent, "system")
    return None


def find_libreoffice(*, app_root: Path | None = None, platform: str | None = None):
    platform = sys.platform if platform is None else platform
    bundle = (application_root() if app_root is None else Path(app_root)) / "tools/libreoffice"
    try:
        return validate_bundle(bundle, platform=platform)
    except OSError, ValueError:
        # Never attempt an incomplete bundled executable. An independently
        # installed engine may still satisfy this optional capability.
        return _system_location(platform, bundle)


class _WindowsDllSearch:
    def __init__(self):
        from ctypes import wintypes

        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.GetDllDirectoryW.argtypes = [wintypes.DWORD, wintypes.LPWSTR]
        self.kernel.GetDllDirectoryW.restype = wintypes.DWORD
        self.kernel.SetDllDirectoryW.argtypes = [wintypes.LPCWSTR]
        self.kernel.SetDllDirectoryW.restype = wintypes.BOOL

    def current_directory(self):
        ctypes.set_last_error(0)
        length = self.kernel.GetDllDirectoryW(0, None)
        if not length:
            if ctypes.get_last_error():
                raise ctypes.WinError(ctypes.get_last_error())
            return None
        buffer = ctypes.create_unicode_buffer(length + 1)
        copied = self.kernel.GetDllDirectoryW(len(buffer), buffer)
        if not copied or copied >= len(buffer):
            raise OSError("Could not snapshot the current DLL search directory")
        return buffer.value

    def set_directory(self, directory):
        if not self.kernel.SetDllDirectoryW(directory):
            raise ctypes.WinError(ctypes.get_last_error())


def _outside_bundle_paths(value, bundle, separator, windows):
    path_module = ntpath if windows else os.path
    anchor = path_module.normcase(path_module.normpath(bundle))
    prefix = anchor.rstrip("\\/") + ("\\" if windows else "/")
    return separator.join(
        part
        for part in value.split(separator)
        if not (
            (normalized := path_module.normcase(path_module.normpath(part.strip('"')))) == anchor
            or normalized.startswith(prefix)
        )
    )


@contextmanager
def external_tool_environment(*, _windows_backend=None):
    """Yield child-only environment; reset/restore frozen Windows DLL search.

    The caller must keep this scope around Popen creation only, not communicate.
    No parent environment variables are rewritten. The process-global Windows
    change is serialized and restored even when process creation fails.
    """
    environment = os.environ.copy()
    if not getattr(sys, "frozen", False):
        yield environment
        return
    windows = sys.platform == "win32"
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        separator = ";" if windows else os.pathsep
        for variable in (
            "PATH",
            "QT_PLUGIN_PATH",
            "QT_QPA_PLATFORM_PLUGIN_PATH",
            "QML2_IMPORT_PATH",
        ):
            if variable in environment:
                cleaned = _outside_bundle_paths(
                    environment[variable], str(bundle), separator, windows
                )
                if cleaned:
                    environment[variable] = cleaned
                else:
                    environment.pop(variable, None)
    if not windows:
        if "LD_LIBRARY_PATH_ORIG" in environment:
            if environment["LD_LIBRARY_PATH_ORIG"]:
                environment["LD_LIBRARY_PATH"] = environment["LD_LIBRARY_PATH_ORIG"]
            else:
                environment.pop("LD_LIBRARY_PATH", None)
        else:
            environment.pop("LD_LIBRARY_PATH", None)
        yield environment
        return
    with _DLL_LOCK:
        backend = _WindowsDllSearch() if _windows_backend is None else _windows_backend
        previous = backend.current_directory()
        try:
            backend.set_directory(None)
            yield environment
        finally:
            backend.set_directory(previous)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", type=Path, required=True)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.output_root is not None:
            ensure_separate_tool_source(args.validate, args.output_root)
        location = validate_bundle(args.validate)
    except ValueError as error:
        print(f"LibreOffice bundle validation failed: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"LibreOffice bundle validation failed: {type(error).__name__}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "valid": True,
                "source": location.source,
                "layout": location.layout,
                "root": str(location.root),
                "executable": str(location.executable),
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
