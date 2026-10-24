"""Stage/install/remove a personal Send to shortcut, without executing file paths."""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path, PureWindowsPath

from filewheel.platforms.windows.native import require_windows


MARKER = "Filewheel explicit-path diagnostic v1"
SHORTCUT_NAME = "Filewheel diagnostic.lnk"


def shortcut_plan(root: PureWindowsPath, executable: PureWindowsPath) -> dict:
    if not root.is_absolute() or not executable.is_absolute():
        raise ValueError("absolute project and Python paths required")
    if any('"' in str(value) or "\x00" in str(value) for value in (root, executable)):
        raise ValueError("invalid shortcut path")
    output = root / "logs" / "invocations"
    # Explorer appends file arguments to this direct executable's command line.
    # No cmd.exe, PowerShell, eval or filename interpolation handles those paths.
    arguments = subprocess.list2cmdline([
        "-m", "filewheel.platforms.windows.explicit_path_diagnostics", "--enable",
        "--output-dir", str(output), "--",
    ])
    return {
        "description": MARKER, "name": SHORTCUT_NAME, "target": str(executable),
        "arguments": arguments, "working_directory": str(root),
        "output_directory": str(output),
        "stage_directory": str(root / "logs" / "sendto-stage"),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("stage", "install", "remove"))
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    require_windows()
    root = args.project_root.resolve(strict=True)
    if not root.is_dir():
        parser.error("project root must be a directory")
    plan = shortcut_plan(PureWindowsPath(str(root)), PureWindowsPath(sys.executable))
    script = Path(__file__).with_name("sendto_shortcut.ps1")
    # Management data travels in a UTF-8 file, not interpolated PowerShell code.
    # No user-selected conversion path participates in shortcut management.
    with tempfile.TemporaryDirectory(prefix="filewheel-shortcut-") as temporary:
        payload = Path(temporary) / "plan.json"
        payload.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        completed = subprocess.run([
            "powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-File", str(script), "-Action", args.action, "-PlanFile", str(payload),
        ], check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
