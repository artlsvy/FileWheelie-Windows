"""Actual QML coordinates: one origin and deterministic concentric lens geometry."""
import math
import os
import time
from pathlib import PureWindowsPath

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
pytest.importorskip('PySide6.QtQuick')
from PySide6.QtCore import QPointF, QUrl
from PySide6.QtQuick import QQuickItem
from PySide6.QtWidgets import QApplication

from filewheel.core.models import TargetResolution
from filewheel.ui.quick_popup import GlassPopup
from filewheel.ui.radial import CapabilityRegistry, PreviewCapability


@pytest.mark.parametrize('count', [2, 3, 4, 5, 6, 8, 12])
@pytest.mark.parametrize('dark', [False, True])
def test_real_qml_lens_and_glare_share_center_at_every_sector(count, dark):
    app = QApplication.instance() or QApplication(['lens-geometry'])
    app.setQuitOnLastWindowClosed(False)
    registry = CapabilityRegistry(tuple(PreviewCapability('.png', 'Image', f'.out{i}', f'F{i}')
                                        for i in range(count)))
    view = GlassPopup(registry, point_mapper=lambda point, screens: point)
    try:
        view.session._dark = dark
        view.session._reduced = True
        view.session.appearanceChanged.emit()
        view.present(TargetResolution(PureWindowsPath('C:/preview/image.png'), 0, (300, 300),
                                      time.monotonic(), source='shell_explicit'))
        view.session.choose(0)
        app.processEvents()
        root = view.rootObject()
        lens = root.findChild(QQuickItem, 'hoverLens')
        glare = root.findChild(QQuickItem, 'pointerGlare')
        assert lens is not None and glare is not None
        inner, outer = lens.property('innerRadius'), lens.property('outerRadius')
        mid, cap = lens.property('centerRadius'), lens.property('capRadius')
        assert 40 < inner < mid < outer < 110
        assert outer - inner == pytest.approx(2 * cap)
        assert lens.property('halfArc') + lens.property('capDegrees') < 180 / count
        theta = lens.property('radians')
        # The cap's tangent tip lies on the same circular cap as both radial
        # endpoints: no radius correction/elliptical bulge is needed by Qt.
        center = (mid * math.sin(theta), -mid * math.cos(theta))
        tip = (lens.property('capTipX'), lens.property('capTipY'))
        assert math.dist(center, tip) == pytest.approx(cap)
        for index in range(count):
            angle = (index + .5) * 2 * math.pi / count
            view.session.hoverAt(120 + 76 * math.sin(angle), 120 - 76 * math.cos(angle))
            root.setProperty('pointerAngle', math.degrees(angle))
            app.processEvents()
            assert view.session.hovered == index
            for item in (lens, glare):
                origin = item.mapToScene(QPointF(0, 0))
                assert origin.x() == pytest.approx(120)
                assert origin.y() == pytest.approx(120)
                assert item.width() == item.height() == 0
            rim = glare.mapToScene(QPointF(0, -104))
            assert math.hypot(rim.x() - 120, rim.y() - 120) == pytest.approx(104)
            image = view.grabWindow()
            assert not image.isNull()
            # Permit a small AA fringe at r110; no disconnected glare/lens
            # fragments may ever appear in the surrounding transparent area.
            for y in range(0, 240, 8):
                for x in range(0, 240, 8):
                    if math.hypot(x - 120, y - 120) > 112:
                        assert image.pixelColor(x, y).alpha() == 0
            assert lens.rotation() % 360 == pytest.approx(math.degrees(angle) % 360)
        assert not view.errors()
    finally:
        view.dismiss()
        view.setSource(QUrl())
        view.deleteLater()
        app.processEvents()


def test_interrupted_animation_wrap_and_click_use_stable_sector_geometry():
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    app = QApplication.instance() or QApplication(['lens-motion'])
    app.setQuitOnLastWindowClosed(False)
    registry = CapabilityRegistry(tuple(PreviewCapability('.png', 'Image', f'.out{i}', f'F{i}')
                                        for i in range(6)))
    view = GlassPopup(registry, point_mapper=lambda point, screens: point)
    try:
        view.present(TargetResolution(PureWindowsPath('C:/preview/image.png'), 0, (300, 300),
                                      time.monotonic(), source='shell_explicit'))
        assert QTest.qWaitForWindowExposed(view, 1000)
        view.session.choose(0)
        app.processEvents()
        root = view.rootObject()
        lens = root.findChild(QQuickItem, 'hoverLens')
        assert view.rootObject().property('animateLens')
        # Includes last-to-first; interrupt every 12ms, well before the145ms ease.
        for index in (5, 0, 1, 4, 3, 0):
            angle = (index + .5) * 2 * math.pi / 6
            point = QPoint(round(120 + 76 * math.sin(angle)), round(120 - 76 * math.cos(angle)))
            current = lens.rotation()
            QTest.mouseMove(view, point)
            root.setProperty('pointerAngle', math.degrees(angle))
            app.processEvents()
            assert view.session.hovered == index
            assert abs(view.rootObject().property('lensRotation') - current) <= 180.01
            QTest.qWait(12)
        QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=point)
        assert view.last_selection.output_extension == '.out0'
        assert view.state.stage == 'confirmation'
    finally:
        view.dismiss()
        view.setSource(QUrl())
        view.deleteLater()
        app.processEvents()
