"""Render real Quick glass over four synthetic desktop scenes, without capture."""
import argparse
import os
import sys
from pathlib import Path
from time import monotonic


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    os.environ.setdefault('QT_QUICK_BACKEND', 'software')
    from pathlib import PureWindowsPath

    from PySide6.QtCore import QEventLoop, QRectF, QTimer
    from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter
    from PySide6.QtWidgets import QApplication

    from filewheel.converters import ConversionManager
    from filewheel.core.models import TargetResolution
    from filewheel.ui.quick_popup import GlassPopup
    app = QApplication([])
    manager = ConversionManager()
    view = GlassPopup(manager.registry, point_mapper=lambda p, s: p)
    board = QImage(960, 720, QImage.Format.Format_ARGB32)
    board.fill(QColor('#101c19'))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    themes = [('Light / Explorer', False, '#f6f7f4', '#34453e'),
              ('Dark / Explorer', True, '#111e1a', '#c9d8cb'),
              ('Light / media backdrop', False, '#58694a', '#f3f2dc'),
              ('Dark / dense document list', True, '#26312e', '#d8e0d8')]
    for index, (title, dark, base, text) in enumerate(themes):
        x, y = (index % 2) * 480, (index // 2) * 360
        painter = QPainter(board)
        painter.fillRect(x + 12, y + 12, 456, 336, QColor(base))
        if index == 2:
            gradient = QLinearGradient(x, y, x + 450, y + 340)
            gradient.setColorAt(0, QColor('#a6b69b'))
            gradient.setColorAt(.5, QColor('#477b70'))
            gradient.setColorAt(1, QColor('#1a3932'))
            painter.fillRect(x + 12, y + 12, 456, 336, gradient)
            for row in range(7):
                painter.setPen(QColor('#7097b3a0'))
                painter.drawArc(QRectF(x - 60 + row * 36, y + 70 + row * 12, 490, 220), 0, 180 * 16)
        painter.setFont(QFont('Sans Serif', 10))
        painter.setPen(QColor(text))
        painter.drawText(x + 30, y + 43, title)
        painter.drawText(x + 30, y + 76, 'Name                         Type       Modified')
        for row in range(7):
            yy = y + 106 + row * 28
            painter.fillRect(x + 28, yy - 11, 12, 12, QColor('#a99664'))
            painter.drawText(x + 48, yy, f'Project image {row + 1}.png          PNG     Today')
            painter.setPen(QColor('#397c8b80'))
            painter.drawLine(x + 25, yy + 9, x + 454, yy + 9)
            painter.setPen(QColor(text))
        painter.end()
        view.present(TargetResolution(PureWindowsPath('C:/preview/image.png'), 0, (260, 260),
                                      monotonic(), source='shell_explicit'))
        view.session._dark = dark
        view.session.appearanceChanged.emit()
        view.session.choose(0)
        view.session.hoverAt(195, 120)
        loop = QEventLoop()
        QTimer.singleShot(210, loop.quit)
        loop.exec()
        image = view.grabWindow()
        if image.isNull() or image.pixelColor(0, 0).alpha() != 0:
            raise RuntimeError('Quick alpha render failed')
        image.save(str(args.output_dir / ('quick-dark.png' if dark else 'quick-light.png')))
        painter = QPainter(board)
        painter.drawImage(x + 206, y + 85, image)
        painter.setPen(QColor(text))
        painter.setFont(QFont('Sans Serif', 8))
        painter.drawText(x + 30, y + 333, 'Actual QML raster, synthetic backdrop; no desktop capture')
        painter.end()
        view.dismiss()
    board.save(str(args.output_dir / 'glass-proof.png'))
    view.setSource('')
    view.deleteLater()
    app.processEvents()


if __name__ == '__main__':
    main()
