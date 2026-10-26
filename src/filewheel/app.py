"""Normal application entry; diagnostics and management need no permanent window."""
import argparse
import sys

from filewheel.converters.debugging import record_failure
from filewheel.runtime import require_runtime


def main(argv=None):
    parser = argparse.ArgumentParser(description='Filewheel local converter')
    parser.add_argument('--tray', action='store_true')
    parser.add_argument('--gui', action='store_true')
    parser.add_argument('--ui-backend', choices=('widgets', 'quick'),
                        help='startup-only renderer; widgets remains default')
    parser.add_argument('--experimental-mouse3', action='store_true')
    parser.add_argument('--startup', choices=('install', 'remove'))
    parser.add_argument('--sendto', choices=('stage', 'install', 'remove'))
    parser.add_argument('--diagnostic', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('paths', nargs='*')
    args = parser.parse_args(argv)
    try:
        require_runtime()
        if args.startup:
            from filewheel.platforms.windows.startup import configure
            configure(args.startup)
            return 0
        if args.sendto:
            from filewheel.paths import application_root
            from filewheel.platforms.windows.sendto import main as sendto_main
            return sendto_main([args.sendto, '--mode', 'gui', '--project-root', str(application_root())])
        if args.self_test:
            from filewheel.selftest import run
            return run(include_quick=args.ui_backend == 'quick')
        from filewheel.platforms.windows.native import require_windows
        require_windows()
        if args.diagnostic:
            from filewheel.converters.debugging import debug_log_path
            from filewheel.platforms.windows.explicit_path_diagnostics import main as diagnose
            return diagnose(['--enable', '--output-dir', str(debug_log_path().parent), '--', *args.paths])
        if args.paths and len(args.paths) != 1:
            parser.error('Exactly one explicit path is supported')
        if args.experimental_mouse3 and args.paths and not args.tray:
            parser.error('--experimental-mouse3 requires tray mode')
        if args.gui and not args.paths:
            parser.error('--gui requires one explicit path')
        from PySide6.QtWidgets import QApplication, QSystemTrayIcon

        from filewheel.platforms.windows.explicit_path_diagnostics import cursor_point
        from filewheel.ui.desktop import DesktopApplication
        from filewheel.ui.single_instance import SingleInstance
        application = QApplication.instance() or QApplication(['Filewheel'])
        application.setQuitOnLastWindowClosed(False)
        packet = {'paths': args.paths, 'point': list(cursor_point())}
        host = None
        def receive(request):
            if host is None:
                return False
            return (host.present_explicit(request['paths'], tuple(request['point']))
                    if request['paths'] else host.ensure_tray())
        broker = SingleInstance(receive)
        outcome = broker.acquire_or_forward(packet)
        if outcome != 'owner':
            return 0 if outcome == 'forwarded' else 3
        tray_mode = args.tray or not args.paths
        if tray_mode and not QSystemTrayIcon.isSystemTrayAvailable():
            broker.close()
            raise RuntimeError('System tray is unavailable; use an explicit file invocation.')
        desktop = host = DesktopApplication(tray=tray_mode, ui_backend=args.ui_backend)
        application._filewheel_desktop = desktop
        application.aboutToQuit.connect(broker.close)
        application._filewheel_broker = broker
        if args.paths and not desktop.present_explicit(args.paths, tuple(packet['point'])):
            desktop.request_quit()
            broker.close()
            return 2
        if args.experimental_mouse3:
            if not desktop.tray_mode:
                parser.error('--experimental-mouse3 requires tray mode')
            desktop.set_experiment(True)
        application._filewheel_desktop = desktop
        try:
            return application.exec()
        finally:
            broker.close()
    except (RuntimeError, OSError, ImportError) as error:
        path = record_failure('application', 'startup', error)
        if sys.stderr is not None:
            print(f'{error}\nLocal debug log: {path}', file=sys.stderr)
        return 1
