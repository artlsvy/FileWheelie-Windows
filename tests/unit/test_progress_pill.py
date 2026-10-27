"""Real Quick surfaces and worker lifetime; native compositor acceptance is separate."""
import os
import time
from pathlib import PureWindowsPath
from unittest.mock import patch

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
pytest.importorskip('PySide6.QtQuick')
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from test_persistent_progress import BlockingManager
from test_quick_popup import pump

from filewheel.core.models import TargetResolution
from filewheel.ui.conversion_controller import ConversionController
from filewheel.ui.desktop import DesktopApplication
from filewheel.ui.placement import Rect
from filewheel.ui.progress_state import ProgressMode, ProgressPresentation, progress_position
from filewheel.ui.quick_popup import GlassPopup


@pytest.fixture
def app():
    instance = QApplication.instance() or QApplication(['pill-tests'])
    instance.setQuitOnLastWindowClosed(False)
    return instance


@pytest.fixture
def target():
    return TargetResolution(PureWindowsPath('C:/fixture/input.png'), 0, (300, 300), time.monotonic(), 'shell_explicit')


@pytest.fixture
def running(app, target):
    manager = BlockingManager()
    coordinator = ConversionController(app)
    view = GlassPopup(manager.registry, manager=manager, coordinator=coordinator, point_mapper=lambda p, s: p)
    view.present(target)
    QCursor.setPos(view.mapToGlobal(QPoint(120, 120)))
    app.processEvents()
    view.session.choose(0)
    view.session.choose(0)
    pump(app, manager.started.is_set)
    yield view, manager, coordinator
    manager.release.set()
    view.shutdown()
    pump(app, lambda: coordinator.job is None)
    view.dismiss_progress()
    if view.progress_view:
        view.progress_view.setSource('')
        view.progress_view.deleteLater()
    view.setSource('')
    view.deleteLater()
    coordinator.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_pure_presentation_transitions_do_not_infer_job_outcome():
    model = ProgressPresentation()
    model.collapse()
    assert model.mode == ProgressMode.SELECTING
    model.start()
    model.collapse()
    assert model.mode == ProgressMode.CONVERTING_COMPACT
    model.expand()
    assert model.mode == ProgressMode.CONVERTING_EXPANDED
    model.collapse()
    model.complete(failed=True)
    assert model.compact and model.mode == ProgressMode.FAILED
    model.expand()
    assert not model.compact and model.mode == ProgressMode.FAILED


@pytest.mark.parametrize('area', [Rect(0, 0, 1920, 1040), Rect(-1536, -200, 1536, 824),
                                 Rect(1920, 0, 1280, 720), Rect(-800, 100, 800, 600)])
def test_pill_placement_uses_monitor_logical_workarea(area):
    # QScreen already supplies logical coordinates; never divide the origin by DPR.
    x, y = progress_position(area)
    assert area.x <= x <= area.x + area.width - 248
    assert area.y <= y <= area.y + area.height - 60
    assert x == round(area.x + area.width - 248 - 16)
    assert y == round(area.y + area.height - 60 - 16)


def test_outside_click_collapses_without_cancel_and_owns_job_in_controller(running, app):
    view, manager, controller = running
    job = view.job
    assert job.parent() is controller
    view.session.activateAt(0, 0)
    assert view.progress_view.isVisible()
    assert view.progress_view.flags() & Qt.WindowType.WindowDoesNotAcceptFocus
    pump(app, lambda: not view._transitioning)
    assert not view.isVisible()
    assert view.progress_view.isVisible()
    assert view.job is job and not job.cancelled.is_set()
    assert view.session.presentation == 'converting_compact'
    assert not view.session.progressKnown  # Stage fractions are not true percent.
    assert not view.present(view.state.target)
    manager.release.set()
    pump(app, lambda: view.job is None)
    assert view.session.presentation == 'succeeded'
    assert view.progress_view.isVisible()
    assert view.last_selection.action == 'converted'


def test_mouse_leave_and_native_hide_retain_discoverable_progress(running, app):
    view, manager, _ = running
    view.session.hoverAt(-30, 120)
    pump(app, lambda: not view._transitioning)
    assert view.progress_view.isVisible()
    assert not view.job.cancelled.is_set()
    view.progress_view.hide()  # Native hide must restore status, never cancel.
    pump(app, view.progress_view.isVisible)
    assert not view.job.cancelled.is_set()
    manager.release.set()
    pump(app, lambda: view.job is None)
    assert view.last_selection.action == 'converted'


def test_completion_mid_morph_uses_correct_result_without_restart(running, app):
    view, manager, _ = running
    view.collapse_progress()
    animation = view.position_animation
    assert view._transitioning
    for _ in range(5):
        view.collapse_progress()
    assert view.position_animation is animation
    manager.release.set()
    pump(app, lambda: view.job is None)
    assert view.session.presentation == 'succeeded'
    pump(app, lambda: not view._transitioning)
    assert view.progress_view.isVisible()
    assert not view.isVisible()
    view.success_timer.setInterval(25)
    pump(app, lambda: view._finished)
    assert view.last_selection.action == 'converted'
    assert not view.progress_view.isVisible()


def test_failure_persists_and_explicit_details_and_ack_are_available(running, app):
    view, manager, _ = running
    manager.fail = True
    view.collapse_progress()
    manager.release.set()
    pump(app, lambda: view.job is None and not view._transitioning)
    assert view.session.presentation == 'failed'
    assert not view.success_timer.isActive()
    view.progress_view.hide()
    pump(app, view.progress_view.isVisible)
    QTest.mouseClick(view.progress_view, Qt.MouseButton.LeftButton, pos=QPoint(30, 25))
    assert view.session.surfaceExpanded
    assert view.progress_view.height() == 190
    view.session.progressAction('Details')
    assert 'Detailed backend failure' in view._details_box.informativeText()
    assert 'conversion-debug.log' in view._details_box.detailedText()
    view._details_box.close()
    view.session.progressAction('Dismiss')
    assert view._finished
    assert view.last_selection.action == 'conversion_failed'


def test_expanded_escape_cancel_then_restart_and_shutdown_are_distinct(running, app, target):
    view, _, controller = running
    view.dismiss()  # Informational dismissal is collapse, not cancellation.
    assert not controller.job.cancelled.is_set()
    view.expand_progress()
    QTest.keyClick(view.progress_view, Qt.Key.Key_Escape)
    assert controller.job.cancelled.is_set()
    pump(app, lambda: view.job is None)
    assert view.last_selection.action == 'conversion_cancelled'
    assert view.session.presentation == 'cancelled'
    view.dismiss_progress()
    assert view.present(target)
    view.session.choose(0)
    view.session.choose(0)
    pump(app, lambda: view.job is not None)
    view.shutdown()
    pump(app, lambda: view.job is None and view._finished)
    assert view.last_selection.action == 'conversion_cancelled'


def test_reduced_motion_low_effects_transition_is_immediate(running):
    view, _, _ = running
    view.session._reduced = True
    view.session._low = True
    view.session.appearanceChanged.emit()
    view.collapse_progress()
    assert not view._transitioning
    assert not view.isVisible()
    assert view.progress_view.isVisible()
    image = view.progress_view.grabWindow()
    assert not image.isNull()
    assert image.pixelColor(0, 0).alpha() == 0
    assert image.pixelColor(30, 30).alpha() == 255


def test_resident_quit_explicitly_cancels_while_repeated_invocations_reject(app, target):
    manager = BlockingManager()
    host = DesktopApplication(tray=True, manager=manager, ui_backend='quick', point_mapper=lambda p, s: p)
    try:
        host._present(target)
        host.popup.session.choose(0)
        host.popup.session.choose(0)
        pump(app, manager.started.is_set)
        assert host.conversions.parent() is host
        host.popup.hide()
        assert not host.present_explicit(['C:/another.png'], (300, 300))
        assert not host.popup.job.cancelled.is_set()
        with patch.object(app, 'quit') as quit_app:
            host.request_quit()
            pump(app, lambda: host.popup.job is None)
            host._finish_quit()
            assert quit_app.called
        assert host.popup.last_selection.action == 'conversion_cancelled'
    finally:
        manager.release.set()
        host.popup.shutdown()
        pump(app, lambda: host.popup.job is None)
        if host.popup.progress_view:
            host.popup.progress_view.setSource('')
            host.popup.progress_view.deleteLater()
        host.popup.setSource('')
        host.popup.deleteLater()
        host.deleteLater()
        app.processEvents()


@pytest.mark.parametrize('scale', ['1', '1.25', '1.5'])
def test_actual_progress_raster_and_logical_pill_click_at_dpi(scale):
    import subprocess
    import sys
    from pathlib import Path
    script = r"""
from pathlib import PureWindowsPath
from time import monotonic
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from filewheel.core.models import TargetResolution
from filewheel.ui.quick_popup import GlassPopup
from filewheel.ui.progress_state import ProgressMode
app = QApplication([])
app.setQuitOnLastWindowClosed(False)
view = GlassPopup(point_mapper=lambda p,s:p)
try:
    view.present(TargetResolution(PureWindowsPath('C:/preview/a.png'),0,(300,300),monotonic(), 'shell_explicit'))
    assert QTest.qWaitForWindowExposed(view, 1000)
    view.session._reduced = True
    view.session.appearanceChanged.emit()
    view.state.stage = 'converting'
    view.session.presentation_state.start()
    view.set_persistent(True)
    view.collapse_progress()
    app.processEvents()
    pill = view.progress_view
    image = pill.grabWindow()
    assert image.width() == round(272 * pill.devicePixelRatio())
    assert image.height() == round(72 * pill.devicePixelRatio())
    assert image.pixelColor(0,0).alpha() == 0
    assert image.pixelColor(round(25*pill.devicePixelRatio()),round(25*pill.devicePixelRatio())).alpha() > 0
    assert pill.flags() & Qt.WindowType.WindowDoesNotAcceptFocus
    QTest.mouseClick(pill, Qt.MouseButton.LeftButton, pos=QPoint(30,25))
    assert view.session.surfaceExpanded
    assert pill.height() == 190
    app.processEvents()
    image = pill.grabWindow()
    assert image.height() == round(190 * pill.devicePixelRatio())
finally:
    view.state.stage='result'
    view.session.presentation_state.mode=ProgressMode.CANCELLED
    view.dismiss_progress()
    if view.progress_view:
        view.progress_view.setSource('')
        view.progress_view.deleteLater()
    view.setSource('')
    view.deleteLater()
    app.processEvents()
"""
    root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QT_SCALE_FACTOR=scale,
               PYTHONPATH=str(root / 'src'))
    result = subprocess.run([sys.executable, '-c', script], env=env, cwd=root,
                            capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stdout + result.stderr



def test_recoverable_progress_load_failure_restores_wheel_without_cancelling(running, app):
    view, manager, _ = running
    view.hide()  # Model native Hide before the lazy surface can load.
    with patch('filewheel.ui.quick_popup.ProgressSurface', side_effect=RuntimeError('missing QML')):
        view.collapse_progress()
        app.processEvents()
    assert view.isVisible()
    assert view.progress_view is None
    assert view.session.presentation == 'converting_expanded'
    assert not view.job.cancelled.is_set()
    manager.release.set()
    pump(app, lambda: view.job is None)
    assert view.last_selection.action == 'converted'
