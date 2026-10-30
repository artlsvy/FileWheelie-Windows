"""Early frozen-process policy; no COM, Qt or optional engine imports here."""

import os
import sys
from pathlib import Path

os.environ["ORT_DISABLE_TELEMETRY"] = "1"

if getattr(sys, "frozen", False) and sys.platform == "win32":
    installed = (Path(sys.executable).parent / 'installation.ini').is_file()
    if installed:
        os.environ.setdefault('FILEWHEEL_UI_BACKEND', 'quick')
    elif (Path(sys._MEIPASS) / 'tools/libreoffice').is_dir():
        # Family onefile: never silently depend on an installed office tool.
        os.environ.setdefault('FILEWHEEL_BUNDLED_TOOLS_ONLY', '1')
        os.environ.setdefault('FILEWHEEL_UI_BACKEND', 'quick')
    # The COM worker consumes this after its owning-thread initialization. Do
    # not import comtypes here: doing so would initialize COM on the GUI thread.
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        raise RuntimeError("Windows local application-data folder is unavailable")
    cache = Path(local) / "Filewheel" / "comtypes_cache" / "py314"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ["FILEWHEEL_COMTYPES_CACHE"] = str(cache)
    # Windowed bootloaders expose None streams; third-party local libraries may
    # call .flush(). App diagnostics use their explicit private log files.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115 - process-lifetime stream
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115 - process-lifetime stream

if getattr(sys, "frozen", False) and sys.platform == "linux":
    os.environ.setdefault('FILEWHEEL_UI_BACKEND','quick')
    os.environ.setdefault('FILEWHEEL_BUNDLED_TOOLS_ONLY','1')
