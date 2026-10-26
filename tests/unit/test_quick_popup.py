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
    pump(app, lambda view=view: view.job is None)
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
        pump(app, lambda view=view: view.job is None)
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
        pump(app, lambda view=view: view.job is None)
        view.setSource('')
        view.deleteLater()
        app.processEvents()


def test_real_qml_pointer_keyboard_and_center_events(popup, app, target):
    from PySide6.QtCore import QPoint
    from PySide6.QtTest import QTest
    popup.present(target)
    assert QTest.qWaitForWindowExposed(popup, 1000)
    QTest.mouseMove(popup, QPoint(195, 120))
    pump(app, lambda: popup.session.hovered == 0)
    QTest.mouseClick(popup, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                     QPoint(195, 120))
    assert popup.state.stage == 'formats'
    QTest.keyClick(popup, Qt.Key.Key_Right)
    assert popup.session.keyboardIndex == 0
    QTest.mouseClick(popup, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                     QPoint(120, 120))
    assert popup.state.stage == 'categories'
    QTest.keyClick(popup, Qt.Key.Key_Escape)
    assert not popup.isVisible()


def test_native_hide_finishes_once_for_transient_invocation(popup, app, target):
    completions = []
    popup.finished.connect(lambda: completions.append(True))
    popup.present(target)
    popup.hide()  # Models the native Qt.Popup outside-dismissal hide path.
    app.processEvents()
    assert completions == [True]
    assert popup.state.stage == 'closed'
    popup.dismiss()
    assert completions == [True]


def test_reduced_motion_low_effects_and_shortest_arc_keep_hit_regions(popup, app, target):
    popup.present(target)
    popup.session.choose(0)
    root = popup.rootObject()
    popup.session._reduced = True
    popup.session._low = True
    popup.session.appearanceChanged.emit()
    assert root.property('animateLens') is False
    popup.session.hoverAt(140, 45)
    first = root.property('lensRotation')
    # Cross the top boundary (last/first sector); never spin around a full circle.
    popup.session.hoverAt(100, 45)
    second = root.property('lensRotation')
    assert abs(second - first) <= 180
    assert popup.session.hovered == hit_test(100, 45, len(popup.state.options))
    assert not popup.errors()


@pytest.mark.parametrize('dark', [False, True])
@pytest.mark.parametrize('low_effects', [False, True])
def test_rendered_material_contrast_over_black_white_and_opaque_fallback(popup, app, target,
                                                                        dark, low_effects):
    from filewheel.ui.theme import contrast_ratio
    popup.present(target)
    popup.session._dark = dark
    popup.session._low = low_effects
    popup.session._reduced = True
    popup.session.appearanceChanged.emit()
    popup.session.choose(0)
    popup.session.hoverAt(195, 120)
    app.processEvents()
    image = popup.grabWindow()
    foreground = popup.rootObject().property('foreground').name()
    # Sample actual rendered material near opaque text, away from glyphs/rims.
    for x, y in ((196, 105), (196, 137), (44, 105), (44, 137), (120, 50)):
        color = image.pixelColor(x, y)
        for background in (0, 255):
            channels = [round(channel * color.alphaF() + background * (1 - color.alphaF()))
                        for channel in (color.red(), color.green(), color.blue())]
            composite = '#' + ''.join(f'{channel:02x}' for channel in channels)
            assert contrast_ratio(foreground, composite) >= 4.5
    assert image.pixelColor(0, 0).alpha() == 0
    assert (image.pixelColor(120, 50).alpha() == 255) is low_effects


def test_opt_in_trace_distinguishes_preparation_from_queued_render(app, target, tmp_path):
    from filewheel.performance import TimingRecorder
    trace = TimingRecorder(tmp_path / 'quick.json', launch_start=time.monotonic())
    with patch('filewheel.ui.quick_popup.get_recorder', return_value=trace):
        view = GlassPopup(point_mapper=lambda p, s: p)
    try:
        view.present(target)
        pump(app, lambda: any(row['stage'] == 'quick_present_to_frame' for row in trace.snapshot()))
        view.session.hoverAt(195, 120)
        pump(app, lambda: any(row['stage'] == 'quick_move_to_frame' for row in trace.snapshot()))
        view.session.choose(0)
        pump(app, lambda: any(row['stage'] == 'quick_choose_to_frame' for row in trace.snapshot()))
        stages = [row['stage'] for row in trace.snapshot()]
        assert stages.count('launch_to_quick_frame') == 1
        assert 'quick_present_to_sync' in stages
        assert 'paint_cpu' not in stages  # Never report GUI preparation as GPU CPU timing.
        assert not (tmp_path / 'quick.json').exists()  # No per-frame disk writes.
        assert all(row['duration_ms'] >= 0 for row in trace.snapshot())
    finally:
        view.dismiss()
        view.setSource('')
        view.deleteLater()
        app.processEvents()


def test_swap_does_not_credit_input_arriving_after_scene_synchronization(popup, tmp_path):
    from filewheel.performance import TimingRecorder
    popup._timings = TimingRecorder(tmp_path / 'batch.json')
    # Deterministic threaded-render ordering, without requiring a GPU in CI.
    popup.mark_pending('present_to_paint')
    popup._capture_frame_requests()
    popup.mark_pending('move_to_paint')  # New GUI input while the old frame renders.
    popup._record_queued_frame()
    assert [row['stage'] for row in popup._timings.snapshot()] == ['quick_present_to_frame']
    popup._capture_frame_requests()
    popup._record_queued_frame()
    assert [row['stage'] for row in popup._timings.snapshot()] == [
        'quick_present_to_frame', 'quick_move_to_frame']


def test_quick_conversion_cancel_persistence_and_error_feedback(app, target):
    from test_persistent_progress import BlockingManager
    for fails in (False, True):
        manager = BlockingManager(fail=fails)
        view = GlassPopup(manager.registry, manager=manager, point_mapper=lambda p, s: p)
        try:
            view.present(target)
            view.session.choose(0)
            view.session.choose(0)
            pump(app, manager.started.is_set)
            app.sendEvent(view, QFocusEvent(QEvent.Type.FocusOut))
            view.session.activateAt(0, 0)
            app.processEvents()
            assert view.isVisible()
            assert not view.job.cancelled.is_set()
            if fails:
                manager.release.set()
            else:
                view.session.keyAction(Qt.Key.Key_Escape)
                assert view.session.statusTitle == 'Stopping'
                assert view.job.cancelled.is_set()
            pump(app, lambda view=view: view.job is None)
            assert view.state.stage == 'result'
            assert view.session.statusTitle == ('Failed' if fails else 'Cancelled')
            assert view.last_selection.action == ('conversion_failed' if fails else 'conversion_cancelled')
            assert view.isVisible()
            assert view.session.detail
        finally:
            manager.release.set()
            view.dismiss()
            pump(app, lambda view=view: view.job is None)
            view.setSource('')
            view.deleteLater()
            app.processEvents()
