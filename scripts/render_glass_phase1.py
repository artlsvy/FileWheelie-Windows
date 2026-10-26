"""Actual QML geometry proof: reference hover states and 2–8 option fixtures.

Uses only preview registries, no file IO/conversion. Backdrops are synthetic,
not Windows screenshots. --scene-dir can point at a saved pre-fix QML pair.
Run once per QT_SCALE_FACTOR for separate 100%/150% renders.
"""
import argparse
import math
import os
import sys
from pathlib import Path, PureWindowsPath
from time import monotonic


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--scene-dir', type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    os.environ.setdefault('QT_QUICK_BACKEND', 'software')
    from PySide6.QtCore import QEventLoop, QPoint, QRect, QTimer
    from PySide6.QtGui import QColor, QCursor, QFont, QImage, QPainter
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from filewheel.core.models import TargetResolution
    from filewheel.ui.quick_popup import GlassPopup
    from filewheel.ui.radial import CapabilityRegistry, PreviewCapability
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    def wait(ms=190):
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def grab(count, index, dark, reduced=False, reference=False):
        options = {}
        if args.scene_dir:
            options['_scene_file'] = args.scene_dir / 'GlassWheel.qml'
        if not reference:
            labels = ('JPEG', 'PNG', 'WebP', 'TIFF', 'BMP', 'GIF', 'AVIF', 'ICO')
            registry = CapabilityRegistry(tuple(PreviewCapability('.fixture', 'Image', f'.f{i}', labels[i])
                                                for i in range(count)))
            options['registry'] = registry
        view = GlassPopup(point_mapper=lambda p, s: p, **options)
        try:
            extension = 'pdf' if reference else 'fixture'
            target = TargetResolution(PureWindowsPath(f'C:/preview/geometry.{extension}'), 0,
                                      (300, 300), monotonic(), source='shell_explicit')
            view.present(target)
            assert QTest.qWaitForWindowExposed(view, 1000)
            view.session._dark, view.session._reduced = dark, reduced
            view.session.appearanceChanged.emit()
            if not reference:
                view.session.choose(0)
            angle = (index + .5) * 2 * math.pi / count
            point = QPoint(round(120 + 76 * math.sin(angle)), round(120 - 76 * math.cos(angle)))
            app.processEvents()
            QCursor.setPos(view.mapToGlobal(point))
            QTest.mouseMove(view, point)
            app.processEvents()
            view.session.hoverAt(point.x(), point.y())
            view.rootObject().setProperty('pointerAngle', math.degrees(angle))
            wait()
            assert view.session.hovered == index, (count, index, view.session.hovered)
            result = view.grabWindow()
            if result.isNull() or not view.isVisible() or result.pixelColor(0, 0).alpha():
                raise RuntimeError('Actual Quick render/alpha failed')
            # Keep full-resolution RGBA snapshots; boards normalize logical size.
            return result.copy()
        finally:
            view.dismiss()
            view.setSource('')
            view.deleteLater()
            app.processEvents()

    def board_image(width, height):
        result = QImage(width, height, QImage.Format.Format_ARGB32)
        result.fill(QColor('#101916'))
        return result

    def cell(board, image, x, y, title, dark=True):
        painter = QPainter(board)
        painter.fillRect(x, y, 280, 300, QColor('#181c1a' if dark else '#eef0e9'))
        painter.setPen(QColor('#829087' if dark else '#899286'))
        painter.setFont(QFont('Sans Serif', 9))
        painter.drawText(x + 10, y + 21, title)
        for row in range(8):
            painter.drawText(x + 12, y + 54 + row * 27, f'▱  Project document {row+1}.pdf     Today')
        # PNG has a DPR; explicit rect scales to logical 240px on this board.
        painter.drawImage(QRect(x + 20, y + 38, 240, 240), image)
        painter.end()

    reference_board = board_image(840, 600)
    for dark in (True, False):
        for col, (reference, name, index) in enumerate(((1, 'Text', 2), (2, 'Image', 0), (3, 'Docs', 1))):
            image = grab(3, index, dark, reference=True)
            image.save(str(args.output_dir / f'ref{reference}-{name.lower()}-{"dark" if dark else "light"}.png'))
            cell(reference_board, image, col * 280, 0 if dark else 300, f'Reference {reference}: {name} / {"dark" if dark else "light"}', dark)
    reference_board.save(str(args.output_dir / 'references.png'))

    counts = (2, 3, 4, 5, 6, 8)
    matrix = board_image(8 * 280, len(counts) * 300)
    for row, count in enumerate(counts):
        for index in range(count):
            image = grab(count, index, True)
            cell(matrix, image, index * 280, row * 300, f'{count} options / sector {index + 1}')
    matrix.save(str(args.output_dir / 'all-sectors.png'))
    image = grab(6, 4, False, reduced=True)
    image.save(str(args.output_dir / 'reduced-motion-light.png'))
    print(f'Rendered actual Quick proof to {args.output_dir}; scale={os.getenv("QT_SCALE_FACTOR", "1")}')


if __name__ == '__main__':
    main()
