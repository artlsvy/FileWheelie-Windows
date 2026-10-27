"""Selection fades and finite progress recovery; not native Windows acceptance."""
import math
import os
from dataclasses import replace
from pathlib import PureWindowsPath

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
pytest.importorskip('PySide6.QtQuick')
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QCursor
from PySide6.QtTest import QTest
from shiboken6 import isValid
from test_progress_pill import app as app  # noqa: PLC0414 - shared pytest fixture
from test_progress_pill import running as running  # noqa: PLC0414 - shared pytest fixture
from test_progress_pill import target as target  # noqa: PLC0414 - shared pytest fixture
from test_quick_popup import popup as popup  # noqa: PLC0414 - shared pytest fixture
from test_quick_popup import pump

from filewheel.ui.quick_geometry import hit_test, inside_dismiss_boundary


def test_tolerant_boundary_does_not_enlarge_click_targets(popup, app, target):
    for degrees in range(360):
        theta = math.radians(degrees)
        assert inside_dismiss_boundary(120 + 117.9 * math.sin(theta), 120 - 117.9 * math.cos(theta))
        assert not inside_dismiss_boundary(120 + 118.1 * math.sin(theta), 120 - 118.1 * math.cos(theta))
    assert not inside_dismiss_boundary(float('nan'), 120)
    popup.present(target)
    QCursor.setPos(popup.mapToGlobal(QPoint(234, 120)))
    popup.session.hoverAt(234, 120)
    assert popup.session.hovered == hit_test(234, 120, 2) == -1
    assert not popup.leave_timer.isActive()
    QTest.qWait(150)
    assert popup.isVisible()
    popup.session.activateAt(234, 120)
    assert popup.last_selection is None
    assert not popup.isVisible()  # An actual outside click retains native semantics.


def test_entrance_hit_test_is_immediate_and_exit_callback_cannot_close_reopen(popup, app, target):
    popup.present(target)
    root = popup.rootObject()
    assert root.property('selectionOpacity') == 0
    assert root.scale() == 1  # Selection optics never transform the MouseArea.
    popup.session.activateAt(195, 120)
    assert popup.state.stage == 'formats'
    assert root.property('selectionOpacity') == 1
    popup._begin_selection_exit()
    generation, serial = popup._generation, popup._selection_serial
    assert popup._selection_exiting
    popup.present(replace(target, path=PureWindowsPath('C:/fixture/next.png')))
    popup._finish_selection_exit(generation, serial)
    QTest.qWait(160)
    assert popup.isVisible()
    assert popup.state.stage == 'categories'
    assert root.property('selectionOpacity') == 1
    popup.session.keyAction(Qt.Key.Key_Escape)
    assert not popup.isVisible()


def test_leave_debounce_then_fade_is_separate_from_morph(popup, app, target):
    popup.present(target)
    QCursor.setPos(popup.mapToGlobal(QPoint(239, 120)))
    popup.session.hoverAt(239, 120)
    assert popup.leave_timer.interval() == 100
    QTest.qWait(60)
    assert not popup._selection_exiting
    assert popup.isVisible()
    pump(app, lambda: popup._selection_exiting)
    assert popup.isVisible()
    assert popup.rootObject().property('collapsing') is False
    pump(app, lambda: not popup.isVisible())


def test_reduced_selection_motion_is_immediate(popup, app, target):
    for flag in ('_reduced', '_low'):
        setattr(popup.session, flag, True)
        popup.session.appearanceChanged.emit()
        popup.present(target)
        assert popup.rootObject().property('selectionOpacity') == 1
        popup._begin_selection_exit()
        assert not popup.isVisible()
        setattr(popup.session, flag, False)


def test_stopped_invisible_entrance_cannot_stick_transition(running, app):
    view, _, controller = running
    view.collapse_progress()
    surface = view.progress_view
    view.position_animation.stop()
    surface.entrance_animation.stop()
    surface.rootObject().setProperty('entrance', 0.)
    view.transition_timer.stop()  # Simulate interrupted coordination too.
    assert view._transitioning
    # Independent, finite recovery handles it without another outside event.
    pump(app, lambda: not view._transitioning)
    assert surface.isVisible()
    assert surface.rootObject().property('entrance') == 1
    assert not controller.job.cancelled.is_set()
    # The old early-return path must normalize an invisible visible Tool as well.
    surface.rootObject().setProperty('entrance', 0.)
    view.collapse_progress()
    assert surface.rootObject().property('entrance') == 1


def test_collapse_expand_collapse_ignores_stale_callbacks_and_restores_hide(running, app):
    view, _, controller = running
    view.collapse_progress()
    generation, serial = view._generation, view._progress_serial
    view.expand_progress()
    view._finish_collapse(generation, serial)
    view._finish_expiry(generation, serial)
    assert view.session.surfaceExpanded
    assert view.progress_view.height() == 190
    assert not view._finished
    view.collapse_progress()
    view.progress_view.entrance_animation.stop()
    view.progress_view.rootObject().setProperty('entrance', 0.)
    view.progress_view.hide()
    pump(app, lambda: view.progress_view.isVisible() and view.progress_view.rootObject().property('entrance') == 1)
    assert not controller.job.cancelled.is_set()


def test_destroyed_native_surface_is_recreated_without_losing_job(running, app):
    view, _, controller = running
    view.collapse_progress()
    surface = view.progress_view
    surface.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    pump(app, lambda: view.progress_view is not None and isValid(view.progress_view)
         and view.progress_view is not surface and view.progress_view.isVisible())
    assert not isValid(surface)
    assert view.progress_view.rootObject().property('entrance') == 1
    assert not controller.job.cancelled.is_set()


def test_repeated_conversions_do_not_reuse_old_success_or_hide_callbacks(running, app, target):
    view, manager, _ = running
    for index in range(3):
        view.collapse_progress()
        generation, serial = view._generation, view._progress_serial
        manager.release.set()
        pump(app, lambda: view.job is None and not view._transitioning)
        assert view.last_selection.action == 'converted'
        view.dismiss_progress()
        manager.release.clear()
        manager.started.clear()
        assert view.present(target)
        view.session.choose(0)
        view.session.choose(0)
        pump(app, manager.started.is_set)
        view._finish_expiry(generation, serial)
        view._finish_collapse(generation, serial)
        view._native_progress_hide(generation)
        assert view.job is not None and not view.job.cancelled.is_set()
        assert view.isVisible()
        assert not view._finished
        if index == 2:
            view.collapse_progress()
            view.session.request_cancel()
            pump(app, lambda: view.job is None)
            assert view.last_selection.action == 'conversion_cancelled'
            pump(app, lambda: not view._transitioning)
            assert view.progress_view.isVisible()


def test_redundant_completed_collapse_keeps_success_expiry(running, app):
    view, manager, _ = running
    view.collapse_progress()
    manager.release.set()
    pump(app, lambda: view.job is None and not view._transitioning)
    serial = view._progress_serial
    view.collapse_progress()
    view.collapse_progress()
    assert view._progress_serial == serial
    view.success_timer.setInterval(25)
    pump(app, lambda: view._finished)
    assert view.last_selection.action == 'converted'


def test_new_conversion_while_old_success_visible_does_not_revive_old_surface(running, app, target):
    view, manager, _ = running
    view.collapse_progress()
    manager.release.set()
    pump(app, lambda: view.job is None and not view._transitioning)
    surface = view.progress_view
    assert surface.isVisible()
    manager.release.clear()
    manager.started.clear()
    assert view.present(target)
    QCursor.setPos(view.mapToGlobal(QPoint(120, 120)))
    view.session.choose(0)
    view.session.choose(0)
    app.processEvents()
    assert view.isVisible()
    assert not surface.isVisible()
    assert not view.session.presentation_state.compact
    assert not view.job.cancelled.is_set()


def test_recreated_completed_surface_keeps_original_success_expiry(running, app):
    view, manager, _ = running
    view.collapse_progress()
    manager.release.set()
    pump(app, lambda: view.job is None and not view._transitioning)
    view.success_timer.setInterval(30)
    surface = view.progress_view
    surface.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    pump(app, lambda: view.progress_view is not None and view.progress_view is not surface)
    assert view.progress_view.isVisible()
    pump(app, lambda: view._finished)
    assert view.last_selection.action == 'converted'
