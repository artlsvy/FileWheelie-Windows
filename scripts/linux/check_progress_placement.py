"""Finite native-Wayland wheel/pill regression; synthetic status, no conversion.

Uses the production KWin bridge and real Qt Quick surfaces. Saves rendered
images and compositor frame/work-area evidence, then unloads its owned scripts.
"""

import argparse
import json
import os
from pathlib import Path, PurePosixPath
from time import monotonic

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWidgets import QApplication

from filewheel.core.models import TargetResolution
from filewheel.platforms.linux.kwin import KWinBridge
from filewheel.ui.quick_popup import GlassPopup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--reduced-motion", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to replace output folder")
    args.output.mkdir(parents=True)
    app = QApplication(["Filewheel placement check"])
    app.setQuitOnLastWindowClosed(False)
    if app.platformName() != "wayland":
        raise SystemExit("Native Wayland required; no X11/offscreen substitution")
    bridge = KWinBridge()
    view = GlassPopup(point_mapper=lambda point, screens: point)
    view.session._reduced = args.reduced_motion
    view.session._dark = args.dark
    view.session.appearanceChanged.emit()
    result = {
        "platform": app.platformName(),
        "dark": args.dark,
        "reduced_motion": args.reduced_motion,
        "samples": [],
        "screens": [],
    }
    for screen in app.screens():
        g, a = screen.geometry(), screen.availableGeometry()
        result["screens"].append(
            {
                "name": screen.name(),
                "qt_dpr": screen.devicePixelRatio(),
                "geometry": [g.x(), g.y(), g.width(), g.height()],
                "qt_available": [a.x(), a.y(), a.width(), a.height()],
            }
        )
    original = bridge.deliver

    def collect(data):
        if "sample" in data:
            result["samples"].append(data["sample"])
        original(data)

    bridge.deliver = collect
    stages = [
        "converting-compact",
        "converting-expanded",
        "failed-compact",
        "failed-expanded",
        "compact-again",
        "expanded-again",
    ]
    finished = False

    def finish():
        nonlocal finished
        if finished:
            return
        finished = True
        valid = len(result["samples"]) == len(stages)
        for sample in result["samples"]:
            if len(sample["windows"]) != 1:
                valid = False
            for window in sample["windows"]:
                x, y, width, height = window["frame"]
                ax, ay, aw, ah = window["area"]
                window["inside_work_area"] = (
                    x >= ax
                    and y >= ay
                    and x + width <= ax + aw + 0.01
                    and y + height <= ay + ah + 0.01
                )
                valid &= (
                    window["inside_work_area"]
                    and window["native_class"] == "KWin::XdgToplevelWindow"
                )
        result["passed"] = bool(valid)
        (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
        view._finish()
        if view.progress_view:
            view.progress_view.setSource(QUrl())
        view.setSource(QUrl())
        bridge.close()
        view.deleteLater()
        app.exit(0 if valid else 1)

    def capture(index):
        surface = view.progress_view
        if surface is None or not surface.grabWindow().save(
            str(args.output / (stages[index] + ".png"))
        ):
            finish()
            return
        script = """
var rows=[];
workspace.windowList().forEach(function(w) {
 if(w.pid!==APP_PID || w.caption!=='Filewheel progress')return;
 var g=w.frameGeometry,a=workspace.clientArea(KWin.MaximizeArea,w);
 rows.push({native_class:String(w).split('(')[0],frame:[g.x,g.y,g.width,g.height],area:[a.x,a.y,a.width,a.height]});
});
callDBus(DEST,'/org/filewheel/Position','org.filewheel.Position','Report',JSON.stringify({token:TOKEN,point:[workspace.cursorPos.x,workspace.cursorPos.y],sample:{stage:STAGE,windows:rows}}));
""".replace("APP_PID", str(os.getpid())).replace("STAGE", json.dumps(stages[index]))
        bridge.run(script, lambda point: change(index + 1))

    def change(index):
        if finished:
            return
        if index >= len(stages):
            finish()
            return
        if index == 2:
            view.state.stage = "result"
            view.session._status = "Failed"
            view.session._detail = "Placement check only; no conversion was run"
            view.session.presentation_state.complete(failed=True)
            view.session._refresh()
            view.completed_progress()
        elif "expanded" in stages[index]:
            view.expand_progress()
        else:
            view.collapse_progress()
        QTimer.singleShot(500, lambda: capture(index))

    def start(point):
        if point is None:
            finish()
            return
        view.present(
            TargetResolution(
                PurePosixPath("/tmp/Placement check.png"),
                0,
                point,
                monotonic(),
                source="linux_explicit",
            )
        )
        view.set_persistent(True)
        view.state.stage = "converting"
        view.session._status, view.session._progress = "Converting", 0.5
        view.session.presentation_state.start()
        view.session._refresh()
        QTimer.singleShot(250, lambda: change(0))

    bridge.install_placement(start)
    QTimer.singleShot(15000, finish)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
