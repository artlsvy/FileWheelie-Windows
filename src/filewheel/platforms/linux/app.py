"""Linux entry: explicit validated targets through the shared desktop owner."""

import os
from pathlib import Path


def main(args):
    if args.sendto or args.diagnostic or args.ui_stress_test:
        raise RuntimeError("That Windows-specific entry point is unavailable on Linux")
    if args.startup:
        from filewheel.platforms.linux.startup import configure

        configure(args.startup)
        return 0
    if args.self_test:
        from filewheel.selftest import run

        return run(include_quick=args.ui_backend == "quick")
    if len(args.paths) > 1 or (args.gui and not args.paths):
        raise RuntimeError("Supply exactly one absolute file path after --")
    from PySide6.QtGui import QCursor
    from PySide6.QtWidgets import QApplication, QFileDialog, QSystemTrayIcon

    from filewheel.ui.desktop import DesktopApplication
    from filewheel.ui.single_instance import SingleInstance

    app = QApplication.instance() or QApplication(["Filewheel"])
    app.setQuitOnLastWindowClosed(False)
    tray = args.tray or not args.paths
    if tray and not QSystemTrayIcon.isSystemTrayAvailable():
        path, _ = QFileDialog.getOpenFileName(None, "Filewheel — choose one file")
        if not path:
            return 0
        args.paths = [path]
        tray = False
    root = Path(os.environ.get("XDG_RUNTIME_DIR", "/run/user/" + str(os.getuid())))
    if not root.is_absolute() or root.stat().st_uid != os.getuid():
        raise RuntimeError("A current-user XDG runtime directory is required")
    # DISPLAY is used only to distinguish X11 sessions, not to claim Wayland access.
    import hashlib

    session = os.getenv("WAYLAND_DISPLAY") or os.getenv("DISPLAY") or "offscreen"
    directory = root / "filewheel" / hashlib.sha256(session.encode()).hexdigest()[:12]
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    point = QCursor.pos()
    if app.platformName() == "wayland":
        point = app.primaryScreen().availableGeometry().center()
    host = None

    def receive(packet):
        return (
            host.present_explicit(packet["paths"], tuple(packet["point"]))
            if packet["paths"]
            else host.ensure_tray()
        )

    broker = SingleInstance(receive, directory=directory)
    packet = {"paths": args.paths, "point": [point.x(), point.y()]}
    outcome = broker.acquire_or_forward(packet)
    if outcome != "owner":
        return 0 if outcome == "forwarded" else 3
    try:
        host = DesktopApplication(tray=tray, ui_backend=args.ui_backend, auto_start=False)
        app._filewheel_desktop = host
        if args.paths and not host.present_explicit(args.paths, tuple(packet["point"])):
            host.request_quit()
            return 2
        return app.exec()
    finally:
        broker.close()
