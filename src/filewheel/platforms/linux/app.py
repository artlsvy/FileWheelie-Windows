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
    if args.paths:
        from filewheel.platforms.linux.paths import validate_paths

        validation = validate_paths(args.paths)
        if validation.path is None:
            raise RuntimeError("Input rejected: " + str(validation.rejection))
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
    kwin = None
    generation = 0

    def present(paths, fallback, *, source=None, captured=None):
        nonlocal generation
        from time import monotonic, monotonic_ns

        check = host.controller.handle_explicit(
            paths, point=fallback, timestamp=monotonic(), inspect_file=host.inspector
        )
        if check.target is None:
            host.notify("Input rejected: " + str(check.rejection))
            return False
        generation += 1
        serial = generation

        def at_point(point):
            if serial != generation or host.quitting:
                return
            if source == "dolphin_click" and not host.experimental_enabled:
                return
            if captured is not None and monotonic_ns() - captured > 2_000_000_000:
                host.notify("Click expired; try again.")
                return
            if point is None:
                host.notify("KWin cursor lookup failed; click again.")
                return
            host.present_explicit(paths, point, source=source)

        if kwin is not None:
            kwin.request_point(at_point)
            return True
        return host.present_explicit(paths, fallback, source=source)

    def receive(packet):
        if host is None or host.quitting:
            return False
        return (
            present(packet["paths"], tuple(packet["point"]))
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
        if app.platformName() == "wayland":
            from filewheel.platforms.linux.kwin import KWinBridge

            try:
                kwin = KWinBridge(host)
            except RuntimeError:
                if args.private_dolphin:
                    raise
                # Other compositors still support explicit files; placement is compositor chosen.

        def start(_point=None):
            try:
                if kwin is not None and _point is None:
                    raise RuntimeError("KWin placement bridge did not start")
                if args.private_dolphin:
                    from filewheel.platforms.linux.dolphin_bridge import DolphinBridge

                    bridge = DolphinBridge(args.private_dolphin, host)
                    bridge.clicked.connect(
                        lambda path, captured: present(
                            [path], (0, 0), source="dolphin_click", captured=captured
                        )
                    )
                    bridge.error.connect(
                        lambda error: host.notify(error) if not host.quitting else None
                    )
                    host.extra_resources.append(bridge)
                    host.linux_bridge = bridge
                    from filewheel import preferences

                    host.set_experiment(preferences.wheel_enabled(), persist=False)
                    bridge.start(args.dolphin_folder or str(Path.home()))
                if args.paths:
                    present(args.paths, tuple(packet["point"]))
            except (RuntimeError, OSError, ImportError) as error:
                from filewheel.converters.debugging import record_failure

                record_failure("linux", "desktop_bootstrap", error)
                host.notify(str(error))
                host.request_quit()

        if kwin is not None:
            kwin.install_placement(start)
        else:
            start()
        return app.exec()
    finally:
        if kwin is not None:
            kwin.close()
        broker.close()
