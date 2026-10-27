"""Separate Windows Quick preview and validated explicit file invocation."""
import argparse
import os
import sys
from pathlib import Path, PureWindowsPath
from time import monotonic


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', help='Absolute Windows path; actual conversion options')
    parser.add_argument('--screenshot', type=Path, help='Preview-only offscreen PNG output')
    parser.add_argument('--preview-format', default='.png', choices=('.png', '.pdf', '.docx'))
    args = parser.parse_args(argv)
    if args.screenshot and args.file:
        parser.error('--screenshot is only for the no-conversion preview')
    if os.getenv('QT_QPA_PLATFORM') == 'offscreen':
        os.environ.setdefault('QT_QUICK_BACKEND', 'software')
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from filewheel.converters import ConversionManager
    from filewheel.core.controller import InvocationController
    from filewheel.core.models import TargetResolution
    from filewheel.ui.quick_popup import GlassPopup
    app = QApplication.instance() or QApplication(['Filewheel glass prototype'])
    app.setQuitOnLastWindowClosed(False)
    manager = ConversionManager()
    if args.file:
        from filewheel.platforms.windows.explicit_path_diagnostics import cursor_point, inspect_file
        from filewheel.platforms.windows.native import require_windows
        require_windows()
        result = InvocationController().handle_explicit([args.file], point=cursor_point(),
                                                       timestamp=monotonic(), inspect_file=inspect_file)
        if result.target is None:
            parser.error(f'Input rejected: {result.rejection}')
        target = result.target
        popup = GlassPopup(manager.registry, manager=manager)
    else:
        # A fabricated path is explicitly preview-only, never sent to an engine.
        point = app.primaryScreen().availableGeometry().center()
        target = TargetResolution(PureWindowsPath('C:/preview/Example' + args.preview_format),
                                  0, (point.x(), point.y()), monotonic(), source='shell_explicit')
        popup = GlassPopup(manager.registry, point_mapper=lambda point, screens: point)
    popup.finished.connect(app.quit)
    popup.present(target)
    if args.screenshot:
        def capture():
            if not popup.grabWindow().save(str(args.screenshot)):
                print('Screenshot failed', file=sys.stderr)
                app.exit(2)
            else:
                popup.dismiss()
        QTimer.singleShot(120, capture)
    result = app.exec()
    popup.setSource('')
    popup.deleteLater()
    app.processEvents()
    return result


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()
    raise SystemExit(main())
