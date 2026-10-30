"""Opt-in five-second KWin scripted-effect API probe, with owned cleanup.

No pointer interception or conversion. Only middle presses over Dolphin are
logged, with a unique prefix and no paths/coordinates. Run with system Python.
"""

import argparse
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from time import sleep

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--report", type=Path, required=True)
parser.add_argument("--seconds", type=int, default=5)
args = parser.parse_args()
if not 1 <= args.seconds <= 60:
    parser.error("--seconds must be between 1 and 60")
if args.report.exists():
    parser.error("Report already exists")
name = "filewheel-probe-" + uuid.uuid4().hex
root = Path.home() / ".local/share/kwin/effects" / name
root.mkdir(parents=True)
(root / "contents/code").mkdir(parents=True)
(root / "metadata.json").write_text(
    json.dumps(
        {
            "KPackageStructure": "KWin/Effect",
            "KPlugin": {
                "Id": name,
                "Name": "Temporary Filewheel API Probe",
                "Version": "1",
                "License": "AGPL-3.0",
                "EnabledByDefault": False,
            },
            "X-Plasma-API": "javascript",
            "X-Plasma-MainScript": "code/main.js",
            "X-KDE-Ordering": 99,
            "X-KWin-Exclusive-Category": "",
        }
    )
)
(root / "contents/code/main.js").write_text(
    'console.info("'
    + name
    + ' READY mouseChanged="+typeof effects.mouseChanged);\neffects.mouseChanged.connect(function(pos,old,buttons,oldbuttons) { if ((buttons & 4) && !(oldbuttons & 4) && effects.activeWindow && effects.activeWindow.resourceClass === "org.kde.dolphin") console.info("'
    + name
    + ' MIDDLE_DOLPHIN"); });'
)
env = dict(os.environ, DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/1000/bus")


def call(method):
    r = subprocess.run(
        [
            "gdbus",
            "call",
            "--session",
            "--dest",
            "org.kde.KWin",
            "--object-path",
            "/Effects",
            "--method",
            "org.kde.kwin.Effects." + method,
            name,
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=4,
        check=False,
    )
    return {"returncode": r.returncode, "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}


try:
    loaded = call("loadEffect")
    print("LOAD", loaded, flush=True)
    if "true" in loaded["stdout"]:
        sleep(args.seconds)
    r = subprocess.run(
        [
            "journalctl",
            "--user",
            "-u",
            "plasma-kwin_wayland.service",
            "--since",
            "30 seconds ago",
            "--no-pager",
            "-o",
            "cat",
        ],
        capture_output=True,
        text=True,
        timeout=4,
        check=False,
    )
    lines = [s for s in r.stdout.splitlines() if name in s]
    print("OWN_LOGS", lines)
    with args.report.open("x") as stream:
        json.dump(
            {"load": loaded, "own_log_lines": lines, "hardware_gesture_verified": False},
            stream,
            indent=2,
        )
finally:
    print("UNLOAD", call("unloadEffect"))
    shutil.rmtree(root)
