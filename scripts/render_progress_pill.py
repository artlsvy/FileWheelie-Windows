"""Render real Quick progress states with a controlled preview worker, no conversion."""
import argparse
import os
import sys
from pathlib import Path, PureWindowsPath
from threading import Event
from time import monotonic


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    os.environ.setdefault('QT_QUICK_BACKEND', 'software')
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
    from PySide6.QtCore import QEventLoop, QPoint, QRect, QTimer
    from PySide6.QtGui import QColor, QCursor, QFont, QImage, QPainter
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from filewheel.converters.base import ConversionCancelled, ConversionError, ConversionResult
    from filewheel.core.models import TargetResolution
    from filewheel.ui.quick_popup import GlassPopup
    from filewheel.ui.radial import DEFAULT_PREVIEW_REGISTRY

    class PreviewWorker:
        registry = DEFAULT_PREVIEW_REGISTRY

        def __init__(self, fail=False):
            self.release = Event()
            self.fail = fail

        def convert(self, source, extension, *, progress, cancel):
            progress(.42, 'Preview worker: stage fraction, not true percent')
            while not self.release.wait(.01):
                if cancel.is_set():
                    raise ConversionCancelled('Preview cancellation')
            if self.fail:
                raise ConversionError('Preview local parser failure')
            return ConversionResult((Path('/preview/output.jpg'),), (), 'preview-worker')

    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    def wait(ms):
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def pump(predicate):
        deadline = monotonic() + 3
        while not predicate() and monotonic() < deadline:
            wait(5)
        assert predicate()

    board = QImage(1200, 420, QImage.Format.Format_ARGB32)
    board.fill(QColor('#151f1a'))
    captures = []
    for fails in (False, True):
        worker = PreviewWorker(fails)
        view = GlassPopup(worker.registry, manager=worker, point_mapper=lambda p, s: p)
        try:
            view.session._dark = True
            view.session.appearanceChanged.emit()
            view.present(TargetResolution(PureWindowsPath('C:/preview/photo.png'), 0,
                                          (300, 300), monotonic(), source='shell_explicit'))
            assert QTest.qWaitForWindowExposed(view, 1000)
            QCursor.setPos(view.mapToGlobal(QPoint(120, 120)))
            view.session.choose(0)
            view.session.choose(0)
            wait(35)
            if not fails:
                captures.append(('Expanded', view.grabWindow()))
            view.collapse_progress()
            wait(95)
            if not fails:
                captures.append(('Transition wheel', view.grabWindow()))
                captures.append(('Transition pill', view.progress_view.grabWindow()))
            wait(150)
            if not fails:
                captures.append(('Compact', view.progress_view.grabWindow()))
            worker.release.set()
            pump(lambda view=view: view.job is None)
            wait(230)
            if fails:
                view.expand_progress()
                wait(40)
                captures.append(('Failed details', view.progress_view.grabWindow()))
            else:
                captures.append(('Converted', view.progress_view.grabWindow()))
        finally:
            worker.release.set()
            view.shutdown()
            pump(lambda view=view: view.job is None)
            view.dismiss_progress()
            if view.progress_view:
                view.progress_view.setSource('')
                view.progress_view.deleteLater()
            view.setSource('')
            view.deleteLater()
            app.processEvents()

    for index, (label, image) in enumerate(captures):
        if image.isNull():
            raise RuntimeError('Empty Quick progress render')
        image.save(str(args.output_dir / (label.lower().replace(' ', '-') + '.png')))
        painter = QPainter(board)
        x, y = (index % 3) * 400, (index // 3) * 210
        painter.setFont(QFont('Sans Serif', 10))
        painter.setPen(QColor('#efe9d9'))
        painter.drawText(x + 14, y + 21, label)
        target = QRect(x + 14, y + 32, min(image.width(), 360), min(image.height(), 170))
        # Keep raw native captures beside this normalized proof board.
        if image.width() == image.height():
            target.setWidth(170)
            target.setHeight(170)
        painter.drawImage(target, image)
        painter.end()
    board.save(str(args.output_dir / 'progress-proof.png'))
    print('Actual Quick frames; controlled preview worker; no source/output conversion performed')


if __name__ == '__main__':
    main()
