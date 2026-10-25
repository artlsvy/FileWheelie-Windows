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


def shortcut_plan(root: PureWindowsPath, executable: PureWindowsPath, mode="diagnostic", *, frozen=False) -> dict:
    if mode not in ("diagnostic", "gui"):
        raise ValueError("unknown launcher mode")
    if not root.is_absolute() or not executable.is_absolute():
        raise ValueError("absolute project and Python paths required")
    if any('"' in str(value) or "\x00" in str(value) for value in (root, executable)):
        raise ValueError("invalid shortcut path")
    if not frozen and mode == "gui" and executable.name.casefold() == "python.exe":
        executable = executable.with_name("pythonw.exe")
    output = root / "logs" / "invocations"
    # Explorer appends file arguments to this direct executable's command line.
    # No cmd.exe, PowerShell, eval or filename interpolation handles those paths.
    if frozen:
        options = ['--gui'] if mode == 'gui' else ['--diagnostic']
        prefix = []
    else:
        options = (['--gui'] if mode == 'gui' else
                   ['--enable', '--output-dir', str(output)])
        prefix = ['-m', 'filewheel' if mode == 'gui' else
                  'filewheel.platforms.windows.explicit_path_diagnostics']
    arguments = subprocess.list2cmdline([*prefix, *options, '--'])
    return {
        "description": MARKER if mode == "diagnostic" else "Filewheel radial preview v1",
        "name": SHORTCUT_NAME if mode == "diagnostic" else "Filewheel preview.lnk",
        "target": str(executable),
        "arguments": arguments,
        "previous_arguments": ([subprocess.list2cmdline(["-m", "filewheel.platforms.windows.explicit_path_diagnostics", "--gui", "--"])]
                               if mode == "gui" and not frozen else []),
        "working_directory": str(root),
        "output_directory": str(output),
        "stage_directory": str(root / "logs" / "sendto-stage"),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("stage", "install", "remove"))
    parser.add_argument("--mode", choices=("diagnostic", "gui"), default="diagnostic")
    from filewheel.paths import application_root
    parser.add_argument("--project-root", type=Path, default=application_root() if getattr(sys, "frozen", False) else Path.cwd())
    args = parser.parse_args(argv)
    require_windows()
    root = args.project_root.resolve(strict=True)
    if not root.is_dir():
        parser.error("project root must be a directory")
    plan = shortcut_plan(PureWindowsPath(str(root)), PureWindowsPath(sys.executable), args.mode, frozen=getattr(sys, "frozen", False))
    script = Path(__file__).with_name("sendto_shortcut.ps1")
    # Management data travels in a UTF-8 file, not interpolated PowerShell code.
    # No user-selected conversion path participates in shortcut management.
    with tempfile.TemporaryDirectory(prefix="filewheel-shortcut-") as temporary:
        payload = Path(temporary) / "plan.json"
        payload.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        completed = subprocess.run([
            "powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-File", str(script), "-Action", args.action, "-PlanFile", str(payload),
        ], check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
