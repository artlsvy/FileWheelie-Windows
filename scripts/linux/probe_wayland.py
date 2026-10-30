"""Bounded native Wayland API/placement probe; never converts or captures input.

Run with system Python (PyGObject/AT-SPI), passing the PySide6 Python separately.
Creates only owned temporary windows/scripts and unloads the KWin script on exit.
"""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from time import monotonic

QT_PROBE = """
import json, sys
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QLabel
app = QApplication(['FilewheelWaylandProbe'])
QGuiApplication.setDesktopFileName('org.filewheel.WaylandProbe')
view = QLabel('Filewheel\\nWayland placement probe')
view.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
view.setStyleSheet('background:#173e32;color:#f5efdf;border-radius:100px;')
view.setAlignment(Qt.AlignCenter)
view.resize(220,220)
view.move(80,90)
view.show()
def report():
    r=view.geometry()
    with open(sys.argv[1], 'w') as f:
        json.dump({'platform':app.platformName(),'requested':[80,90],
                   'qt_geometry':[r.x(),r.y(),r.width(),r.height()]},f)
QTimer.singleShot(1000,report)
QTimer.singleShot(10000,app.quit)
app.exec()
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qt-python", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error("Report already exists")
    runtime = Path("/run/user") / str(os.getuid())
    if runtime.stat().st_uid != os.getuid() or not (runtime / "wayland-0").is_socket():
        parser.error("Expected an owned native wayland-0 session; no fallback is used")
    os.environ["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=" + str(runtime / "bus")
    import gi

    gi.require_version("Gio", "2.0")
    gi.require_version("Atspi", "2.0")
    from gi.repository import Atspi, Gio, GLib

    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

    def call(destination, path, interface, method, signature=None, values=()):
        params = GLib.Variant(signature, values) if signature else None
        return bus.call_sync(
            destination, path, interface, method, params, None, Gio.DBusCallFlags.NONE, 2000, None
        ).unpack()

    kwin_owner = call(
        "org.freedesktop.DBus",
        "/org/freedesktop/DBus",
        "org.freedesktop.DBus",
        "GetNameOwner",
        "(s)",
        ("org.kde.KWin",),
    )[0]
    result = {
        "gate": "incomplete",
        "kwin": [],
        "qt": None,
        "fixture_items": [],
        "input_capture": "not demonstrated; no global input listener installed",
    }
    xml = '<node><interface name="org.filewheel.Probe"><method name="Report"><arg type="s" direction="in"/></method></interface></node>'

    def receive(connection, sender, path, interface, method, parameters, invocation):
        raw = parameters.unpack()[0]
        if sender != kwin_owner or len(raw) > 8192:
            invocation.return_dbus_error("org.filewheel.Rejected", "Invalid report")
            return
        result["kwin"].append(json.loads(raw))
        invocation.return_value(None)

    info = Gio.DBusNodeInfo.new_for_xml(xml)
    registered = bus.register_object("/Probe", info.interfaces[0], receive, None, None)
    processes, scripts = [], []
    env = dict(
        os.environ,
        XDG_RUNTIME_DIR=str(runtime),
        WAYLAND_DISPLAY="wayland-0",
        QT_QPA_PLATFORM="wayland",
        QT_LINUX_ACCESSIBILITY_ALWAYS_ON="1",
    )
    loop = GLib.MainLoop()
    try:
        with tempfile.TemporaryDirectory(prefix="filewheel-wayland-") as folder:
            root = Path(folder)
            fixtures = root / "fixtures"
            fixtures.mkdir()
            for name in ("report.txt", "report.csv", "unicode-æøå.txt"):
                (fixtures / name).write_text("Filewheel fixture only\n")
            qt_result = root / "qt.json"
            output = (root / "process.log").open("w")
            try:
                processes.append(
                    subprocess.Popen(
                        [str(args.qt_python.absolute()), "-c", QT_PROBE, str(qt_result)],
                        env=env,
                        stdout=output,
                        stderr=output,
                    )
                )
                processes.append(
                    subprocess.Popen(
                        ["dolphin", "--new-window", str(fixtures)],
                        env=env,
                        stdout=output,
                        stderr=output,
                    )
                )

                def inspect():
                    script = root / "inspect.js"
                    script.write_text(
                        """
var r = {cursorAvailable: typeof workspace.cursorPos,
 cursorSignal: typeof workspace.cursorPosChanged,
 mouseSignal: typeof workspace.mouseChanged,
 registerPointerShortcut: typeof registerPointerShortcut,
 startMousePolling: typeof workspace.startMousePolling, windows: [], fixtureWindows: []};
workspace.windowList().forEach(function(w) {
 if (w.pid === DOLPHIN_PID) r.fixtureWindows.push({nativeClass: String(w).split("(")[0]});
 if (w.pid !== PROBE_PID) return;
 var g=w.frameGeometry;
 r.windows.push({before:[g.x,g.y,g.width,g.height]});
 w.frameGeometry={x:80,y:90,width:g.width,height:g.height};
 g=w.frameGeometry;
 r.windows[r.windows.length-1].after=[g.x,g.y,g.width,g.height];
});
callDBus(DEST, '/Probe', 'org.filewheel.Probe', 'Report', JSON.stringify(r));
""".replace("PROBE_PID", str(processes[0].pid))
                        .replace("DOLPHIN_PID", str(processes[1].pid))
                        .replace("DEST", json.dumps(bus.get_unique_name()))
                    )
                    name = "filewheel-feasibility-" + str(os.getpid())
                    sid = call(
                        "org.kde.KWin",
                        "/Scripting",
                        "org.kde.kwin.Scripting",
                        "loadScript",
                        "(ss)",
                        (str(script), name),
                    )[0]
                    if sid < 0:
                        raise RuntimeError("KWin refused probe script")
                    scripts.append(name)
                    call(
                        "org.kde.KWin", "/Scripting/Script" + str(sid), "org.kde.kwin.Script", "run"
                    )
                    return False

                GLib.timeout_add(3000, inspect)
                GLib.timeout_add(6000, lambda: (loop.quit(), False)[1])
                loop.run()
                if qt_result.exists():
                    result["qt"] = json.loads(qt_result.read_text())
                Atspi.set_timeout(300, 500)
                desktop = Atspi.get_desktop(0)
                deadline = monotonic() + 4
                queue = []
                for i in range(min(desktop.get_child_count(), 32)):
                    app = desktop.get_child_at_index(i)
                    if app.get_process_id() == processes[1].pid:
                        queue.append(app)
                visited = 0
                while queue and visited < 800 and monotonic() < deadline:
                    item = queue.pop(0)
                    visited += 1
                    if item.get_name() in ("report.txt", "report.csv", "unicode-æøå.txt"):
                        component = item.get_component_iface()
                        bounds = (
                            component.get_extents(Atspi.CoordType.SCREEN) if component else None
                        )
                        result["fixture_items"].append(
                            {
                                "name": item.get_name(),
                                "description": item.get_description(),
                                "attributes": item.get_attributes(),
                                "interfaces": item.get_interfaces(),
                                "screen_bounds": [bounds.x, bounds.y, bounds.width, bounds.height]
                                if bounds
                                else None,
                            }
                        )
                    queue.extend(
                        item.get_child_at_index(i) for i in range(min(item.get_child_count(), 40))
                    )
                result["fixture_nodes_visited"] = visited
            finally:
                output.close()
    finally:
        for name in scripts:
            call(
                "org.kde.KWin",
                "/Scripting",
                "org.kde.kwin.Scripting",
                "unloadScript",
                "(s)",
                (name,),
            )
        for process in processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
        bus.unregister_object(registered)
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
