"""Actual QML loading/raster fallback and shared job navigation; not Windows QA."""
import math
import os
import time
from pathlib import PureWindowsPath
from unittest.mock import patch

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
pytest.importorskip('PySide6.QtQuick')
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QFocusEvent
from PySide6.QtWidgets import QApplication

from filewheel.core.models import TargetResolution
from filewheel.ui.quick_geometry import hit_test
from filewheel.ui.quick_popup import GlassPopup


def pump(app, predicate, seconds=5):
    deadline = time.monotonic() + seconds
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.003)
    assert predicate()


@pytest.fixture
def app():
    application = QApplication.instance() or QApplication(['quick-tests'])
    application.setQuitOnLastWindowClosed(False)
    return application


@pytest.fixture
def target():
    return TargetResolution(PureWindowsPath('C:/test/input.png'), 0, (300, 300),
                            time.monotonic(), source='shell_explicit')


@pytest.fixture
def popup(app):
    view = GlassPopup(point_mapper=lambda p, s: p)
    yield view
    view.dismiss()
    pump(app, lambda: view.job is None)
    view.setSource('')
    view.deleteLater()
    app.processEvents()


@pytest.mark.parametrize('count', [1, 2, 3, 5, 8])
def test_geometry_sector_centers_are_stable_under_visual_emphasis(count):
    for index in range(count):
        angle = (index + .5) * 2 * math.pi / count
        x, y = 120 + 76 * math.sin(angle), 120 - 76 * math.cos(angle)
        assert hit_test(x, y, count) == index
    assert hit_test(120, 120, count) == -2
    assert hit_test(0, 0, count) == -1
    assert hit_test(float('nan'), 1, count) == -1


def test_qml_loads_alpha_and_does_not_use_painted_canvas(popup, app, target):
    assert not popup.errors()
    assert popup.present(target)
    pump(app, lambda: popup.isVisible())
    # Software scenegraph grab is an actual renderer output, not a mocked image.
    app.processEvents()
    image = popup.grabWindow()
    assert not image.isNull()
    assert image.width() == 240
    assert image.pixelColor(0, 0).alpha() == 0
    assert image.pixelColor(120, 120).alpha() > 0
    assert popup.state.stage == 'categories'


def test_navigation_hover_selection_back_escape_reopen(popup, app, target):
    popup.present(target)
    popup.session.hoverAt(195, 120)
    assert popup.session.hovered == 0
    popup.session.keyAction(Qt.Key.Key_Return)
    assert popup.state.stage == 'formats'
    popup.session.keyAction(Qt.Key.Key_Right)
    assert popup.session.keyboardIndex == 0
    popup.session.keyAction(Qt.Key.Key_Backspace)
    assert popup.state.stage == 'categories'
    popup.session.choose(-1)
    assert popup.last_selection is None
    popup.session.choose(0)
    popup.session.choose(0)
    assert popup.state.stage == 'confirmation'
    assert popup.last_selection.action == 'dry_run_only'
    popup.session.keyAction(Qt.Key.Key_Escape)
    assert not popup.isVisible()
    assert popup.present(target)
    assert popup.state.stage == 'categories'
    assert popup.session.hovered == -1
    assert popup.last_selection is None


def test_outside_and_focus_dismiss_but_status_is_persistent(popup, app, target):
    popup.present(target)
    popup.session.activateAt(1, 1)
    assert not popup.isVisible()
    popup.present(target)
    with patch.object(popup, 'isActive', return_value=False):
        app.sendEvent(popup, QFocusEvent(QEvent.Type.FocusOut))
        app.processEvents()
    assert not popup.isVisible()
    popup.present(target)
    popup.state.stage = 'result'
    popup.set_persistent(True)
    with patch.object(popup, 'isActive', return_value=False):
        app.sendEvent(popup, QFocusEvent(QEvent.Type.FocusOut))
        app.processEvents()
    popup.session.activateAt(0, 0)
    assert popup.isVisible()
    popup.session.keyAction(Qt.Key.Key_Escape)
    assert not popup.isVisible()


def test_invalid_target_and_position_do_not_open(popup, target):
    assert not popup.present(object())
    assert not popup.isVisible()
    popup.point_mapper = lambda p, s: (float('nan'), 5)
    with pytest.raises(RuntimeError):
        popup.present(target)
    assert not popup.isVisible()


def test_actual_conversion_uses_shared_spawned_manager_and_keeps_input(app, tmp_path, target):
    from PIL import Image

    from filewheel.converters import ConversionManager, Registry
    from filewheel.converters.images import PillowEngine
    source = tmp_path / 'image.png'
    Image.new('RGBA', (20, 12), (70, 40, 130, 0)).save(source)
    before = source.read_bytes()
    manager = ConversionManager(Registry((PillowEngine(),)))
    view = GlassPopup(manager.registry, manager=manager, source_mapper=lambda path: source,
                      point_mapper=lambda p, s: p)
    try:
        view.present(target)
        view.session.choose(0)
        view.session.choose(0)
        assert view.job is not None
        assert not view.present(target)  # Busy requests cannot reset a live job.
        pump(app, lambda: view.job is None)
        assert view.state.stage == 'result'
        assert view.last_selection.action == 'converted'
        with Image.open(view.last_selection.outputs[0]) as output:
            assert output.size == (20, 12)
            assert output.format == 'JPEG'
        assert source.read_bytes() == before
        assert not list(tmp_path.glob('.filewheel-*'))
        assert view.isVisible()
    finally:
        view.dismiss()
        pump(app, lambda: view.job is None)
        view.setSource('')
        view.deleteLater()
        app.processEvents()
