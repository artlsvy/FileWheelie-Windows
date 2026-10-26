"""Separate Qt processes are required to exercise startup DPI scaling honestly."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip('PySide6.QtQuick')


@pytest.mark.parametrize('scale', ['1', '1.5'])
def test_actual_qml_pixels_and_logical_hits_at_startup_scale(scale):
    script = r'''
import math
from pathlib import PureWindowsPath
from time import monotonic
from PySide6.QtCore import QPoint, Qt, QUrl
from PySide6.QtGui import QCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from filewheel.core.models import TargetResolution
from filewheel.ui.quick_popup import GlassPopup
from filewheel.ui.radial import CapabilityRegistry, PreviewCapability
app = QApplication([])
app.setQuitOnLastWindowClosed(False)
for count in (2, 3, 4, 5, 6, 8):
    registry = CapabilityRegistry(tuple(PreviewCapability('.png', 'Image', f'.f{i}', f'F{i}') for i in range(count)))
    view = GlassPopup(registry, point_mapper=lambda p, s: p)
    try:
        view.present(TargetResolution(PureWindowsPath('C:/preview/a.png'),0,(300,300),monotonic(), source='shell_explicit'))
        assert QTest.qWaitForWindowExposed(view, 1000)
        QCursor.setPos(view.mapToGlobal(QPoint(120, 120)))
        view.session._reduced = True
        view.session.appearanceChanged.emit()
        view.session.choose(0)
        app.processEvents()
        for index in range(count):
            angle = (index + .5) * 2 * math.pi / count
            point = QPoint(round(120 + 76 * math.sin(angle)), round(120 - 76 * math.cos(angle)))
            QTest.mouseMove(view, point)
            app.processEvents()
            assert view.session.hovered == index, (count, index, view.session.hovered)
        app.processEvents()
        image = view.grabWindow()
        expected = round(240 * view.devicePixelRatio())
        assert image.width() == image.height() == expected, (expected, image.size())
        assert image.pixelColor(0, 0).alpha() == 0
        assert image.pixelColor(expected//2, expected//2).alpha() > 0
        QTest.mouseClick(view, Qt.MouseButton.LeftButton,
                         pos=point)
        assert view.last_selection.output_extension == f'.f{count-1}'
    finally:
        view.dismiss()
        view.setSource(QUrl())
        view.deleteLater()
        app.processEvents()
print('logical hits and physical raster passed')
'''
    root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QT_SCALE_FACTOR=scale,
               PYTHONPATH=str(root / 'src'))
    result = subprocess.run([sys.executable, '-c', script], env=env, cwd=root,
                            capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'logical hits and physical raster passed' in result.stdout
