"""Shell explicit-path launcher; headless diagnostics or optional radial preview."""

import argparse
import ctypes
import json
import os
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath
from time import monotonic
from uuid import uuid4

from filewheel.core.controller import InvocationController
from filewheel.core.explicit_paths import FileCheck
from filewheel.platforms.windows.native import require_windows


def cursor_point() -> tuple[int, int]:
    """Physical desktop coordinates, including negative monitor coordinates."""
    require_windows()
    from ctypes import wintypes

    user = ctypes.WinDLL("user32", use_last_error=True)
    get_point = user.GetPhysicalCursorPos
    get_point.argtypes = [ctypes.POINTER(wintypes.POINT)]
    get_point.restype = wintypes.BOOL
    point = wintypes.POINT()
    if not get_point(ctypes.byref(point)):
        raise ctypes.WinError(ctypes.get_last_error())
    return point.x, point.y


def inspect_file(path: PureWindowsPath) -> FileCheck:
    """Metadata only; file contents are never read or modified."""
    require_windows()
    try:
        info = os.stat(str(path), follow_symlinks=False)
    except FileNotFoundError:
        return FileCheck(exists=False, is_file=False)
    return FileCheck(
        exists=True, is_file=stat.S_ISREG(info.st_mode),
        is_reparse_point=bool(getattr(info, "st_file_attributes", 0) & 0x400),
    )


def resolve_invocation(arguments, point, *, controller=None, inspector=None):
    """Portable test seam; both sources feed the same controller/target DTO."""
    started = monotonic()
    controller = controller if controller is not None else InvocationController()
    inspector = inspector if inspector is not None else inspect_file
    result = controller.handle_explicit(
        arguments, point=point, timestamp=started, inspect_file=inspector,
    )
    target = result.target
    record = {
        "schema_version": 1, "type": "explicit_invocation", "source": "shell_explicit",
        "argument_count": len(arguments), "accepted": target is not None,
        "path": str(target.path) if target is not None else None,
        "point": list(point), "timestamp_monotonic": started,
        "rejection": result.rejection, "elapsed_ms": round((monotonic() - started) * 1000, 3),
        "pid": os.getpid(), "python_version": sys.version.split()[0],
        "action": "diagnostic_only",
    }

    return target, record


def invocation_record(arguments, point, *, controller=None, inspector=None) -> dict:
    """Preserved portable headless diagnostic interface."""
    return resolve_invocation(arguments, point, controller=controller, inspector=inspector)[1]


def show_preview(target):
    # Optional import after validation; headless mode never imports Qt.
    from filewheel.ui.popup import run_popup
    from filewheel.converters import ConversionManager
    manager = ConversionManager()
    return run_popup(target, manager.registry, manager=manager)


def write_invocation(record: dict, *, output: Path | None, directory: Path | None) -> Path:
    if output is None:
        if directory is None:
            raise ValueError("output destination required")
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        output = directory / f"invocation-{stamp}-{os.getpid()}-{uuid4().hex}.jsonl"
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
    return output


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enable", action="store_true", help="opt in to local path diagnostics")
    parser.add_argument("--gui", action="store_true", help="open the radial dry-run preview")
    destination = parser.add_mutually_exclusive_group()
    destination.add_argument("--output", type=Path, help="new JSONL file; never overwritten")
    destination.add_argument("--output-dir", type=Path, help="directory for unique invocation logs")
    parser.add_argument("paths", nargs="*", help="exactly one absolute file path after --")
    args = parser.parse_args(argv)
    if not args.gui and not (args.output or args.output_dir):
        parser.error("headless diagnostics require --output or --output-dir")
    if (not args.gui or args.output or args.output_dir) and not args.enable:
        parser.error("local diagnostic logging requires --enable")
    try:
        require_windows()
        point = cursor_point()
    except (RuntimeError, OSError):
        print("Interactive Windows cursor context unavailable", file=sys.stderr)
        return 3
    target, record = resolve_invocation(args.paths, point)
    if args.gui:
        record["action"] = "radial_preview"
    output = None
    if args.output or args.output_dir:
        try:
            output = write_invocation(record, output=args.output, directory=args.output_dir)
        except (OSError, ValueError):
            print("Could not create a new diagnostic log", file=sys.stderr)
            return 4
    # Legacy redirected Windows streams may not support the input's Unicode.
    # Keep UTF-8 in the local artifact and ASCII escapes on the console.
    print(json.dumps(record, ensure_ascii=True, allow_nan=False))
    if output is not None:
        print(f"Local log: {json.dumps(str(output), ensure_ascii=True)}")
    if target is None:
        return 2
    if args.gui:
        try:
            selection = show_preview(target)
        except ImportError:
            print('GUI dependency missing. Install with: python -m pip install -e ".[ui]"',
                  file=sys.stderr)
            return 5
        except (RuntimeError, OSError) as error:
            from filewheel.ui.desktop_errors import DesktopInitializationError
            diagnostic = ({"stage": error.stage, "details": error.details}
                          if isinstance(error, DesktopInitializationError) else
                          {"stage": "start_popup", "details": {"error_type": type(error).__name__}})
            print(json.dumps({"type": "gui_startup_error", **diagnostic},
                             ensure_ascii=True, allow_nan=False), file=sys.stderr)
            print("GUI desktop initialization failed; see gui_startup_error above", file=sys.stderr)
            return 5
        if selection is not None:
            print(json.dumps({"action": selection.action, "path": str(selection.input_path),
                              "category": selection.category,
                              "original_format": selection.original_format,
                              "destination_format": selection.output_extension,
                              "intended_output": str(selection.intended_path)}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
