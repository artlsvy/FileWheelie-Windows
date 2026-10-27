"""Real Quick F1–F4 frames with a preview worker; no user file conversion."""
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

    from filewheel.converters import ConversionManager
    from filewheel.converters.base import ConversionCancelled, ConversionResult
    from filewheel.core.models import TargetResolution
    from filewheel.ui.quick_popup import GlassPopup

    class PreviewWorker:
        def __init__(self):
            self.registry = ConversionManager().registry
            self.release = Event()

        def convert(self, source, extension, *, progress, cancel):
            while not self.release.wait(.01):
                if cancel.is_set():
                    raise ConversionCancelled('Preview cancelled')
            return ConversionResult((Path('/preview/output.png'),), (), 'preview-worker')

    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    worker = PreviewWorker()
    view = GlassPopup(worker.registry, manager=worker, point_mapper=lambda p, s: p)
    target = TargetResolution(PureWindowsPath('C:/preview/document.pdf'), 0, (300, 300),
                              monotonic(), 'shell_explicit')
    frames = []

    def wait(ms):
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def pump(predicate):
        deadline = monotonic() + 5
        while not predicate() and monotonic() < deadline:
            wait(5)
        assert predicate()

    def capture(label, surface=view):
        image = surface.grabWindow()
        assert not image.isNull()
        frames.append((label, image))

    try:
        view.session._dark = True
        view.session.appearanceChanged.emit()
        view.present(target)
        assert QTest.qWaitForWindowExposed(view, 1000)
        QCursor.setPos(view.mapToGlobal(QPoint(120, 120)))
        wait(35)
        assert 0 < view.rootObject().property('selectionOpacity') < 1
        capture('Opening')
        wait(150)
        QCursor.setPos(view.mapToGlobal(QPoint(185, 82)))
        QTest.mouseMove(view, QPoint(185, 82))
        wait(160)
        capture('Selection')
        view.session.choose(0)
        wait(160)
        capture('Formats')
        view._begin_selection_exit()
        wait(45)
        assert 0 < view.rootObject().property('selectionOpacity') < 1
        capture('Dismissal')
        pump(lambda: not view.isVisible())
        view.present(target)
        QCursor.setPos(view.mapToGlobal(QPoint(120, 120)))
        view.session.choose(0)
        view.session.choose(0)
        view.session.hoverAt(-10, 120)
        pump(lambda: view.progress_view is not None and not view._transitioning)
        capture('Compact', view.progress_view)
        worker.release.set()
        pump(lambda: view.job is None)
        wait(250)
        capture('Completed', view.progress_view)
    finally:
        worker.release.set()
        view.shutdown()
        pump(lambda: view.job is None)
        if view.progress_view is not None:
            view.progress_view.setSource('')
            view.progress_view.deleteLater()
        view.setSource('')
        view.deleteLater()
        app.processEvents()

    board = QImage(960, 600, QImage.Format.Format_ARGB32)
    board.fill(QColor('#17221c'))
    for index, (label, image) in enumerate(frames):
        image.save(str(args.output_dir / (label.lower() + '.png')))
        painter = QPainter(board)
        x, y = (index % 3) * 320, (index // 3) * 300
        painter.setPen(QColor('#f3ecdd'))
        painter.setFont(QFont('Sans Serif', 11))
        painter.drawText(x + 14, y + 25, label)
        painter.drawImage(QRect(x + 14, y + 42, image.width(), image.height()), image)
        painter.end()
    board.save(str(args.output_dir / 'ui-polish-proof.png'))
    print('Actual Qt Quick frames over synthetic background; preview worker only')


if __name__ == '__main__':
    main()
