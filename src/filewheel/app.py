"""Normal application entry; diagnostics and management need no permanent window."""
import argparse
import sys

from filewheel.converters.debugging import record_failure
from filewheel.runtime import require_runtime


def main(argv=None):
    parser = argparse.ArgumentParser(description='Filewheel local converter')
    parser.add_argument('--tray', action='store_true')
    parser.add_argument('--gui', action='store_true')
    parser.add_argument('--experimental-mouse3', action='store_true')
    parser.add_argument('--startup', choices=('install', 'remove'))
    parser.add_argument('--sendto', choices=('stage', 'install', 'remove'))
    parser.add_argument('--diagnostic', action='store_true')
    parser.add_argument('paths', nargs='*')
    args = parser.parse_args(argv)
    try:
        require_runtime()
        if args.startup:
            from filewheel.platforms.windows.startup import configure
            configure(args.startup)
            return 0
        if args.sendto:
            from filewheel.platforms.windows.sendto import main as sendto_main
            return sendto_main([args.sendto, '--mode', 'gui'])
        from filewheel.platforms.windows.native import require_windows
        require_windows()
        if args.diagnostic:
            from filewheel.converters.debugging import debug_log_path
            from filewheel.platforms.windows.explicit_path_diagnostics import main as diagnose
            return diagnose(['--enable', '--output-dir', str(debug_log_path().parent), '--', *args.paths])
        if args.paths and len(args.paths) != 1:
            parser.error('Exactly one explicit path is supported')
        if args.gui and not args.paths:
            parser.error('--gui requires one explicit path')
        from PySide6.QtWidgets import QApplication

        from filewheel.platforms.windows.explicit_path_diagnostics import cursor_point
        from filewheel.ui.desktop import DesktopApplication
        application = QApplication.instance() or QApplication(['Filewheel'])
        application.setQuitOnLastWindowClosed(False)
        desktop = DesktopApplication(tray=args.tray or not args.paths)
        if args.experimental_mouse3:
            if not desktop.tray_mode:
                parser.error('--experimental-mouse3 requires tray mode')
            desktop.set_experiment(True)
        if args.paths and not desktop.present_explicit(args.paths, cursor_point()):
            desktop.request_quit()
            return 2
        application._filewheel_desktop = desktop
        return application.exec()
    except (RuntimeError, OSError) as error:
        path = record_failure('application', 'startup', error)
        if sys.stderr is not None:
            print(f'{error}\nLocal debug log: {path}', file=sys.stderr)
        return 1
