"""Optional scenegraph popup. Controller DTOs and conversion jobs stay unchanged."""
import math
import os
import sys
from dataclasses import replace
from html import escape
from pathlib import Path
from threading import Lock
from time import monotonic

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QEvent,
    QObject,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    Qt,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QColor, QCursor, QDesktopServices
from PySide6.QtQuick import QQuickView, QQuickWindow
from PySide6.QtWidgets import QApplication, QMessageBox, QToolTip
from shiboken6 import isValid

from filewheel.converters.base import ConversionCancelled, ConversionError
from filewheel.converters.debugging import describe_conversion_error, error_details, record_failure
from filewheel.performance import get_recorder
from filewheel.ui.conversion_controller import ConversionController
from filewheel.ui.desktop_errors import DesktopInitializationError
from filewheel.ui.placement import Rect, popup_position
from filewheel.ui.popup import logical_point
from filewheel.ui.progress_state import ProgressMode, ProgressPresentation, progress_position
from filewheel.ui.quick_geometry import SIZE, hit_test, inside_dismiss_boundary
from filewheel.ui.radial import DEFAULT_PREVIEW_REGISTRY, RadialState
from filewheel.ui.render_diagnostics import RenderDiagnostics
from filewheel.ui.theme import glass_palette, normalize_accent


class GlassSession(QObject):
    """Small Qt bridge over the existing navigation state and production worker."""
    optionsChanged = Signal()
    hoverChanged = Signal()
    stageChanged = Signal()
    statusChanged = Signal()
    appearanceChanged = Signal()
    presentationChanged = Signal()

    def __init__(self, view, registry, manager, source_mapper):
        super().__init__(view)
        self.view = view
        self.state = RadialState(registry)
        self.manager, self.source_mapper = manager, source_mapper
        self.coordinator = view.coordinator
        self.coordinator.progress.connect(self._conversion_progress)
        self.coordinator.completed.connect(self._conversion_done)
        self.presentation_state = ProgressPresentation()
        self.last_selection = self.conversion_result = self.conversion_error = None
        self._hovered = self._keyboard = -1
        self._progress = 0.
        self._status = self._detail = ''
        self._dark = QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
        self._accent_color = None
        self._reduced = os.getenv('FILEWHEEL_REDUCED_MOTION') == '1'
        self._low = os.getenv('FILEWHEEL_LOW_EFFECTS') == '1'
        self._moving = True
        QApplication.styleHints().colorSchemeChanged.connect(self._sync_scheme)

    @property
    def job(self):
        return self.coordinator.job

    @Property(str, notify=presentationChanged)
    def presentation(self):
        return self.presentation_state.mode.value

    @Property(bool, notify=presentationChanged)
    def surfaceExpanded(self):
        return not self.presentation_state.compact

    @Property(bool, notify=statusChanged)
    def progressKnown(self):
        # Existing engines report stage fractions, not a trustworthy work ETA.
        # Keep the original values internally; don't advertise arbitrary %.
        return False

    @Slot()
    def expandProgress(self):
        self.view.expand_progress()

    @Slot(str)
    def progressAction(self, action):
        if action == 'Cancel':
            self.request_cancel()
        elif action == 'Compact':
            self.view.collapse_progress()
        elif action == 'Reveal':
            self.view.reveal_output()
        elif action == 'Details':
            self.view.show_details()
        elif action == 'Dismiss':
            self.view.dismiss_progress()

    @Slot()
    def _sync_scheme(self):
        self._dark = QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
        self.appearanceChanged.emit()

    @Property('QVariantList', notify=optionsChanged)
    def labels(self):
        names = {'Document': 'Docs', 'Markdown/Text': 'Text'}
        return [names.get(option, option) if isinstance(option, str) else option.label
                for option in self.state.options]

    @Property(str, notify=stageChanged)
    def stage(self):
        return self.state.stage

    @Property(int, notify=hoverChanged)
    def hovered(self):
        return self._hovered

    @Property(int, notify=hoverChanged)
    def keyboardIndex(self):
        return self._keyboard

    @Property(bool, notify=appearanceChanged)
    def dark(self):
        return self._dark

    @Property('QVariantMap', notify=appearanceChanged)
    def colors(self):
        return glass_palette(self._accent_color, self._dark)

    @Property(bool, notify=appearanceChanged)
    def reducedMotion(self):
        return self._reduced

    @Property(bool, notify=appearanceChanged)
    def lowEffects(self):
        return self._low

    @Property(bool, notify=appearanceChanged)
    def movingLens(self):
        return self._moving

    @Property(float, notify=statusChanged)
    def progress(self):
        return self._progress

    @Property(str, notify=statusChanged)
    def statusTitle(self):
        return self._status

    @Property(str, notify=stageChanged)
    def centerLabel(self):
        return {'formats': 'Back', 'converting': 'Cancel', 'result': 'Done',
                'confirmation': 'Done'}.get(self.stage, 'Esc')

    @Property(str, notify=stageChanged)
    def filename(self):
        return self.state.target.path.name if self.state.target else ''

    @Property(str, notify=statusChanged)
    def detail(self):
        return self._detail

    def _refresh(self):
        self._hovered = self._keyboard = -1
        self.optionsChanged.emit()
        self.stageChanged.emit()
        self.hoverChanged.emit()
        self.statusChanged.emit()

    @Slot(float, float)
    def hoverAt(self, x, y):
        self.view.pointer_boundary(x, y)
        index = hit_test(x, y, len(self.state.options))
        if index == self._hovered:
            return
        self._hovered = index
        self.view.mark_pending('move_to_paint')
        self.hoverChanged.emit()
        if (self.stage == 'result' and index == -2) or self.view._tooltip_text():
            self.view.tooltip_timer.start()
        else:
            self.view.tooltip_timer.stop()
            QToolTip.hideText()

    @Slot()
    def clearHover(self):
        self.view.pointer_exited()
        self._hovered = -1
        self.hoverChanged.emit()
        self.view.tooltip_timer.stop()
        QToolTip.hideText()

    @Slot(float, float)
    def activateAt(self, x, y):
        hit = hit_test(x, y, len(self.state.options))
        if hit == -2:
            self.center()
        elif self.stage in ('categories', 'formats') and hit >= 0:
            self.choose(hit)
        elif hit == -1:
            self.view.collapse_progress() if self.view.persistent else self.view.dismiss()

    @Slot(int)
    def keyAction(self, key):
        if key == Qt.Key.Key_Escape:
            self.request_cancel() if self.job else self.view.dismiss()
        elif key == Qt.Key.Key_Backspace and self.stage == 'formats':
            self.center()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            if self.stage in ('categories', 'formats'):
                self.choose(self._keyboard if self._keyboard >= 0 else max(0, self._hovered))
            else:
                self.center()
        elif self.state.options and key in (Qt.Key.Key_Right, Qt.Key.Key_Down, Qt.Key.Key_Tab,
                                            Qt.Key.Key_Up, Qt.Key.Key_Left, Qt.Key.Key_Home, Qt.Key.Key_End):
            count = len(self.state.options)
            if key == Qt.Key.Key_Home:
                self._keyboard = 0
            elif key == Qt.Key.Key_End:
                self._keyboard = count - 1
            else:
                delta = -1 if key in (Qt.Key.Key_Left, Qt.Key.Key_Up) else 1
                self._keyboard = ((self._keyboard + delta) % count if self._keyboard >= 0
                                  else 0 if delta > 0 else count - 1)
            self._hovered = -1
            self.view.mark_pending('move_to_paint')
            self.hoverChanged.emit()

    def center(self):
        if self.job:
            self.request_cancel()
        elif self.state.back():
            self.view._cancel_selection_motion()
            self.view.mark_pending('choose_to_paint')
            self._refresh()
        else:
            self.view.dismiss()

    def choose(self, index):
        if type(index) is int and 0 <= index < len(self.state.options):
            self.view._cancel_selection_motion()
        self.view.mark_pending('choose_to_paint')
        selection = self.state.choose(index)
        self._refresh()
        if selection is None:
            return
        self.last_selection = selection
        if self.manager is None:
            self._status = 'Preview only'
            self._detail = f'{selection.input_path}\n{selection.intended_path}\nNo file created.'
            self._refresh()
        else:
            self.view.render_diagnostics.sequence += 1
            self.view.render_diagnostics.record('conversion_start')
            self.state.stage = 'converting'
            self._status, self._detail, self._progress = 'Converting', '', 0.
            self.last_selection = replace(selection, action='conversion_started')
            self.view.set_persistent(True)
            self.presentation_state.start()
            self.presentationChanged.emit()
            self._refresh()
            self.coordinator.start(self.manager, self.source_mapper(selection.input_path),
                                   selection.output_extension)
        self.view.selected.emit(self.last_selection)

    def request_cancel(self):
        if self.job:
            self.coordinator.cancel()
            self._status = 'Stopping'
            self.statusChanged.emit()

    def _conversion_progress(self, value, message):
        self._progress = max(0., min(1., value)) if math.isfinite(value) else 0.
        self._detail = message
        self.statusChanged.emit()

    def _conversion_done(self, result, error):
        if error is None and (result is None or not result.outputs):
            error = ConversionError('The conversion produced no output')
        self.conversion_result, self.conversion_error = result, error
        if error:
            cancelled = isinstance(error, ConversionCancelled)
            self._status = 'Cancelled' if cancelled else 'Failed'
            self._detail = describe_conversion_error(error) + '\n' + error_details(error)
            self.last_selection = replace(self.last_selection,
                                          action='conversion_cancelled' if cancelled else 'conversion_failed',
                                          outputs=())
        else:
            self._status, self._progress = 'Converted', 1.
            self._detail = '\n'.join(str(path) for path in result.outputs)
            if result.warnings:
                self._detail += '\n' + '\n'.join(result.warnings)
            self.last_selection = replace(self.last_selection, action='converted',
                                          intended_path=result.outputs[0], outputs=result.outputs)
        self.state.stage = 'result'
        self.presentation_state.complete(failed=error is not None, cancelled=isinstance(error, ConversionCancelled))
        self.presentationChanged.emit()
        self._refresh()
        self.view.completed_progress()
        if self.view._closing:
            self.view._finish()


class GlassPopup(QQuickView):
    """Experimental selectable renderer; same present/finished/job desktop seam."""
    selected = Signal(object)
    finished = Signal()

    def set_accent_color(self, color):
        self.session._accent_color = normalize_accent(color)
        self.session.appearanceChanged.emit()

    def __init__(self, registry=DEFAULT_PREVIEW_REGISTRY, *, point_mapper=logical_point,
                 manager=None, source_mapper=lambda path: Path(str(path)), coordinator=None, _scene_file=None):
        QQuickWindow.setDefaultAlphaBuffer(True)
        super().__init__()
        self.render_diagnostics = RenderDiagnostics(self, 'wheel')
        self.point_mapper = point_mapper
        self.coordinator = coordinator or ConversionController(QApplication.instance())
        self.progress_view = None
        self._details_box = None
        self._transitioning = False
        self._generation = self._progress_serial = self._selection_serial = self._surface_serial = 0
        self._selection_exiting = False
        self._selection_animation = None
        self._progress_load_failed = False
        self._success_expiry_enabled = False
        self._original_area = None
        self._closing = self._changing_flags = False
        self._finished = True
        self._timings = get_recorder()
        self._pending = {}
        self._frame_pending = {}
        self._render_pending = {}
        self._frame_lock = Lock()
        self.frame_count = 0
        self.session = GlassSession(self, registry, manager, source_mapper)
        self.session.presentationChanged.connect(self._trace_presentation)
        self.setColor(QColor('transparent'))
        self.set_persistent(False)
        self.setWidth(SIZE)
        self.setHeight(SIZE)
        self.rootContext().setContextProperty('wheel', self.session)
        scene = Path(_scene_file) if _scene_file is not None else Path(__file__).with_name('qml') / 'GlassWheel.qml'
        self.setSource(QUrl.fromLocalFile(str(scene)))
        if self.status() == QQuickView.Status.Error:
            details = '; '.join(e.toString() for e in self.errors())
            self.setSource(QUrl())
            self.deleteLater()
            raise RuntimeError('Quick scene failed to load: ' + details)
        if self._timings.enabled:
            self.afterAnimating.connect(self._frame_tick)
            self.afterSynchronizing.connect(self._capture_frame_requests, Qt.ConnectionType.DirectConnection)
            self.frameSwapped.connect(self._record_queued_frame, Qt.ConnectionType.DirectConnection)
        self.focus_timer = QTimer(self)
        self.focus_timer.setSingleShot(True)
        self.leave_timer = QTimer(self)
        self.leave_timer.setSingleShot(True)
        self.leave_timer.setInterval(100)
        self.tooltip_timer = QTimer(self)
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.setInterval(450)
        self.tooltip_timer.timeout.connect(lambda: QToolTip.showText(QCursor.pos(), '<pre>' + escape(self._tooltip_text()) + '</pre>'))
        self.transition_timer = QTimer(self)
        self.transition_timer.setSingleShot(True)
        self.success_timer = QTimer(self)
        self.success_timer.setSingleShot(True)
        self.success_timer.setInterval(4500)
        self.expiry_timer = QTimer(self)
        self.expiry_timer.setSingleShot(True)
        self.position_animation = None
        self.selection_timer = QTimer(self)
        self.selection_timer.setSingleShot(True)
        self.recovery_timer = QTimer(self)
        self.recovery_timer.setSingleShot(True)

    @property
    def state(self):
        return self.session.state

    def _trace_presentation(self):
        self.render_diagnostics.snapshot('presentation')
        if self.progress_view is not None and isValid(self.progress_view):
            self.progress_view.render_diagnostics.sequence = self.render_diagnostics.sequence
            self.progress_view.render_diagnostics.snapshot('presentation')

    @property
    def job(self):
        return self.session.job

    @property
    def last_selection(self):
        return self.session.last_selection

    @property
    def persistent(self):
        return self.state.stage in ('converting', 'result')

    def pointer_boundary(self, x, y):
        if self._changing_flags or not self.isVisible():
            return
        if self.state.stage == 'converting' and self._progress_load_failed:
            return  # The durable wheel is the recovery surface, never hide it.
        # MouseArea's rectangle includes transparent corners. Test the actual
        # circle even when the hovered sector remains -1. Do not restart an
        # active debounce for every outside move or dismissal could starve.
        if self.state.stage == 'converting' and not inside_dismiss_boundary(x, y):
            self.collapse_progress()
            return
        if self.state.stage not in ('categories', 'formats') or inside_dismiss_boundary(x, y):
            self.leave_timer.stop()
        elif self.isVisible() and not self.leave_timer.isActive():
            self._arm(self.leave_timer, 100, self._dismiss_if_outside)

    def pointer_exited(self):
        # Qt can emit MouseArea.onExited during our own hide/flag changes.
        # Those are presentation changes, not physical pointer movement.
        if self._changing_flags or not self.isVisible():
            return
        point = self.mapFromGlobal(QCursor.pos())
        self.pointer_boundary(point.x(), point.y())

    def _dismiss_if_outside(self, generation=None):
        if generation is not None and generation != self._generation:
            return
        if not self.isVisible() or self.state.stage not in ('categories', 'formats'):
            return
        # Recheck the current logical cursor after the debounce. Mapping via
        # QWindow avoids applying one DPR to global/mixed-monitor coordinates.
        local = self.mapFromGlobal(QCursor.pos())
        if not inside_dismiss_boundary(local.x(), local.y()):
            self._begin_selection_exit()

    def _tooltip_text(self):
        if self.state.stage == 'formats' and 0 <= self.session.hovered < len(self.state.options):
            return getattr(self.state.options[self.session.hovered], 'description', '')
        return self.session.detail if self.state.stage == 'result' and self.session.hovered == -2 else ''

    def _arm(self, timer, milliseconds, callback, *extra):
        """Capture invocation identity so an already-queued old timeout is inert."""
        timer.stop()
        old_callback = getattr(timer, '_filewheel_callback', None)
        if old_callback is not None:
            timer.timeout.disconnect(old_callback)
        generation = self._generation
        timer._filewheel_callback = lambda: callback(generation, *extra)
        timer.timeout.connect(timer._filewheel_callback)
        timer.start(milliseconds)

    def _cancel_selection_motion(self, *, reset=True):
        self._selection_serial += 1
        self._selection_exiting = False
        if hasattr(self, 'selection_timer'):
            self.selection_timer.stop()
        if self._selection_animation is not None:
            self._selection_animation.stop()
            self._selection_animation.deleteLater()
            self._selection_animation = None
        if reset and self.rootObject() is not None:
            self.rootObject().setProperty('selectionOpacity', 1.)

    def _animate_selection(self, opacity, duration):
        root = self.rootObject()
        group = QParallelAnimationGroup(self)
        for name, final in ((b'selectionOpacity', opacity),):
            animation = QPropertyAnimation(root, name, group)
            animation.setStartValue(root.property(name.decode()))
            animation.setEndValue(final)
            animation.setDuration(duration)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            group.addAnimation(animation)
        self._selection_animation = group
        group.start()

    def _begin_selection_entrance(self):
        if self.session.reducedMotion or self.session.lowEffects:
            return
        self.rootObject().setProperty('selectionOpacity', 0.)
        self._animate_selection(1., 140)

    def _begin_selection_exit(self):
        if self.state.stage not in ('categories', 'formats') or self.job or self._selection_exiting:
            return
        if self.session.reducedMotion or self.session.lowEffects:
            self._finish()
            return
        self._cancel_selection_motion(reset=False)
        self._selection_exiting = True
        serial = self._selection_serial
        self._animate_selection(0., 110)
        self._arm(self.selection_timer, 110, self._finish_selection_exit, serial)

    def _finish_selection_exit(self, generation, serial):
        if (generation == self._generation and serial == self._selection_serial
                and self._selection_exiting and not self.job
                and self.state.stage in ('categories', 'formats')):
            self._finish()

    def mark_pending(self, stage):
        if self._timings.enabled:
            now = monotonic()
            self._pending[stage] = now
            with self._frame_lock:
                self._frame_pending[stage] = now

    def _capture_frame_requests(self):
        # Render thread while GUI is blocked: only requests represented by this
        # synchronized scene may be credited to its subsequent swap. Later GUI
        # input remains pending for the next frame, never the already-rendering one.
        with self._frame_lock:
            self._render_pending, self._frame_pending = self._frame_pending, {}

    def _record_queued_frame(self):
        # Opt-in render-thread observer only: no Qt GUI calls, controller state
        # or IO. This measures queued presentation, not physical display time.
        now = monotonic()
        with self._frame_lock:
            pending, self._render_pending = self._render_pending, {}
        names = {'present_to_paint': 'quick_present_to_frame',
                 'move_to_paint': 'quick_move_to_frame',
                 'choose_to_paint': 'quick_choose_to_frame'}
        for stage, started in pending.items():
            self._timings.record(names[stage], (now - started) * 1000)
        self._timings.record_launch('launch_to_quick_frame', now)

    def _frame_tick(self):
        # afterAnimating is a GUI-thread scenegraph preparation boundary, not a
        # rendered/displayed frame. Queued frame timing is separately opt-in.
        self.frame_count += 1
        if self._timings.enabled:
            now = monotonic()
            for stage, started in self._pending.items():
                name = {'present_to_paint': 'quick_present_to_sync',
                        'move_to_paint': 'quick_move_to_sync',
                        'choose_to_paint': 'quick_choose_to_sync'}[stage]
                self._timings.record(name, (now - started) * 1000)
            self._pending.clear()

    def present(self, target):
        if self.job:
            return False
        self._generation += 1
        self._success_expiry_enabled = False
        self.focus_timer.stop()
        self._cancel_selection_motion()
        self.leave_timer.stop()
        self.success_timer.stop()
        self.expiry_timer.stop()
        self.transition_timer.stop()
        self._hide_progress()
        self._progress_load_failed = False
        self.rootObject().setProperty('morphingAllowed', False)
        self.rootObject().setProperty("collapsing", False)
        self.session.presentation_state = ProgressPresentation()
        self.session.presentationChanged.emit()
        if not self.state.open(target):
            self._finish()
            return False
        self._closing, self._finished = False, False
        self.session.last_selection = self.session.conversion_result = self.session.conversion_error = None
        self.session._status = self.session._detail = ''
        self.session._progress = 0.
        self.session._refresh()
        self.set_persistent(False)
        app = QApplication.instance()
        try:
            point = self.point_mapper(target.point, app.screens())
            screen = app.screenAt(QPoint(round(point[0]), round(point[1])))
            if screen is None:
                self.state.dismiss()
                raise DesktopInitializationError('find_logical_screen', {'logical_point': list(point)})
            area = screen.availableGeometry()
            self._original_area = Rect(area.x(), area.y(), area.width(), area.height())
            x, y = popup_position(point, Rect(area.x(), area.y(), area.width(), area.height()), (SIZE, SIZE))
            if self.screen() != screen:
                self.setScreen(screen)
            self.setPosition(x, y)
        except Exception as error:
            self._finish()
            if isinstance(error, DesktopInitializationError):
                raise
            raise DesktopInitializationError('position_popup', {'error_type': type(error).__name__}) from error
        self.setTitle(f'Filewheel — {target.path.name}')
        self._begin_selection_entrance()
        self.mark_pending('present_to_paint')
        self.show()
        self.raise_()
        self.requestActivate()
        self.rootObject().forceActiveFocus()
        self.update()
        return True

    def set_persistent(self, enabled):
        if self.rootObject() is not None:
            self.rootObject().setProperty('morphingAllowed', bool(enabled))
        if enabled and hasattr(self, 'leave_timer'):
            self.leave_timer.stop()
        kind = Qt.WindowType.Tool if enabled or sys.platform == "linux" else Qt.WindowType.Popup
        flags = (kind | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                 | Qt.WindowType.NoDropShadowWindowHint)
        if self.flags() == flags:
            return
        visible = self.isVisible()
        self._changing_flags = True
        try:
            self.render_diagnostics.record('flags', old=int(self.flags()), new=int(flags))
            # A visible QWindow Popup is registered in Qt's popup/grab stack.
            # Changing it to Tool first leaves the old popup registered: later
            # dialogs receive presses but their releases go to the hidden wheel.
            # Hide with the OLD flags so Qt releases that grab before retyping.
            if visible:
                self.hide()
            self.setFlags(flags)
            if visible:
                self.show()
        finally:
            self._changing_flags = False

    def dismiss(self):
        # Informational dismissal is presentation-only while work is active.
        self.collapse_progress() if self.job else self._finish()

    def shutdown(self):
        """Explicit resident/tray shutdown; distinct from Hide/Close/dismiss."""
        if self.job:
            self._closing = True
            self.session.request_cancel()
        else:
            self._finish()

    def _cancel_progress_motion(self):
        self._progress_serial += 1
        self.transition_timer.stop()
        self.recovery_timer.stop()
        self.expiry_timer.stop()
        self._transitioning = False
        if self.position_animation is not None:
            self.position_animation.stop()
            self.position_animation.deleteLater()
            self.position_animation = None
        if self.progress_view is not None and isValid(self.progress_view):
            self.progress_view.entrance_animation.stop()

    def _current_progress(self, generation, serial):
        return (isValid(self) and generation == self._generation and serial == self._progress_serial
                and self.persistent and not self._finished and not self._closing)

    def _show_status_wheel(self):
        self._cancel_progress_motion()
        self.session.presentation_state.expand()
        self.session.presentationChanged.emit()
        self._cancel_selection_motion()
        self.rootObject().setProperty('morphingAllowed', False)
        self.rootObject().setProperty('collapsing', False)
        self.set_persistent(True)
        self.show()  # No activation: preserve status without taking foreground focus.

    def _ensure_progress(self):
        if (self.progress_view is not None
                and (not isValid(self.progress_view) or self.progress_view.rootObject() is None)):
            self.progress_view = None
        if self.progress_view is None:
            if self._progress_load_failed:
                self._show_status_wheel()
                return None
            try:
                surface = ProgressSurface(self)
                self.progress_view = surface
                surface.render_diagnostics.sequence = self.render_diagnostics.sequence
                self._surface_serial += 1
                serial = self._surface_serial
                surface.destroyed.connect(lambda: self._progress_surface_destroyed(serial))
            except (ImportError, RuntimeError, OSError) as error:
                record_failure('quick', 'create_progress_surface', error)
                self._progress_load_failed = True
                self._show_status_wheel()
                return None
        return self.progress_view

    def _progress_surface_destroyed(self, serial):
        if not isValid(self) or serial != self._surface_serial:
            return
        self.progress_view = None
        success_remaining = self.success_timer.remainingTime()
        resume_success = (self._success_expiry_enabled and self.session.presentation_state.compact
                          and self.session.presentation_state.mode == ProgressMode.SUCCEEDED)
        self._cancel_progress_motion()
        if self.persistent and not self._finished and not self._closing:
            generation, motion = self._generation, self._progress_serial
            QTimer.singleShot(0, lambda: self._recover_progress(generation, motion))
            if resume_success:
                # Keep the original observable-success budget through native
                # recreation; an in-flight fade already reached that deadline.
                self._arm(self.success_timer, max(1, success_remaining), self._expire_success, motion)

    def _recover_progress(self, generation, serial):
        """Finite transition/hide recovery, not a desktop polling loop."""
        if not self._current_progress(generation, serial):
            return
        self.render_diagnostics.snapshot('recovery')
        if self.session.presentation_state.compact:
            self._finish_collapse(generation, serial)
            return
        surface = self._ensure_progress()
        if surface is None:
            return
        surface.entrance_animation.stop()
        surface.rootObject().setProperty('entrance', 1.)
        surface.setHeight(190)
        surface.setPosition(*progress_position(self._original_area or Rect(0, 0, 800, 600), (272, 190)))
        surface.show()

    def collapse_progress(self):
        if self.state.stage not in ('converting', 'result') or self._closing:
            return
        self._cancel_selection_motion()
        surface = self._ensure_progress()
        if surface is None:
            return
        if self._transitioning:
            # A stopped animation must not make the early-return state permanent.
            if (not self.transition_timer.isActive()
                    or surface.entrance_animation.state() == QPropertyAnimation.State.Stopped):
                self._recover_progress(self._generation, self._progress_serial)
            elif not surface.isVisible():
                surface.show()
            return
        was_visible = surface.isVisible()
        old_position = surface.position()
        if was_visible and not self.isVisible() and self.session.presentation_state.compact:
            # Repeated outside events are idempotent. Do not invalidate the
            # success/expiry token or revive a pill that is already fading out.
            if not self.expiry_timer.isActive():
                surface.entrance_animation.stop()
                surface.rootObject().setProperty('entrance', 1.)
            surface.setPosition(*progress_position(self._original_area or Rect(0, 0, 800, 600), (272, 72)))
            return
        self._cancel_progress_motion()
        serial = self._progress_serial
        self.session.presentation_state.collapse()
        self.session.presentationChanged.emit()
        surface.set_accepts_focus(False)
        surface.setHeight(72)
        area = self._original_area or Rect(0, 0, 800, 600)
        destination = QPoint(*progress_position(area, (272, 72)))
        reduced = self.session.reducedMotion or self.session.lowEffects
        if was_visible and not self.isVisible():
            # This surface may have been left at zero opacity by an interrupted
            # expiry/entrance. Native visibility alone does not establish feedback.
            surface.rootObject().setProperty('entrance', 1.)
            surface.setPosition(destination)
            surface.show()
            return
        if surface.screen() != self.screen():
            surface.setScreen(self.screen())
        start = old_position if was_visible else self.position() + QPoint(-16, 84)
        surface.setPosition(destination if reduced else start)
        surface.show()  # Tool + WindowDoesNotAcceptFocus: never activate here.
        self.rootObject().setProperty('collapsing', True)
        self._transitioning = not reduced
        if reduced:
            self._finish_collapse(self._generation, serial)
        else:
            surface.rootObject().setProperty('entrance', 0.)
            self.position_animation = QParallelAnimationGroup(self)
            for axis, initial, final in ((b'x', start.x(), destination.x()), (b'y', start.y(), destination.y())):
                animation = QPropertyAnimation(surface, axis, self.position_animation)
                animation.setDuration(210)
                animation.setStartValue(initial)
                animation.setEndValue(final)
                animation.setEasingCurve(QEasingCurve.Type.OutCubic)
                self.position_animation.addAnimation(animation)
            self.position_animation.start()
            surface.entrance_animation.setDuration(210)
            surface.entrance_animation.setStartValue(0.)
            surface.entrance_animation.setEndValue(1.)
            surface.entrance_animation.start()
            self._arm(self.transition_timer, 210, self._finish_collapse, serial)
            self._arm(self.recovery_timer, 270, self._recover_progress, serial)

    def _finish_collapse(self, generation=None, serial=None):
        generation = self._generation if generation is None else generation
        serial = self._progress_serial if serial is None else serial
        if not self._current_progress(generation, serial):
            return
        self._transitioning = False
        self.transition_timer.stop()
        self.recovery_timer.stop()
        if self.position_animation is not None:
            self.position_animation.stop()
        if self.session.presentation_state.compact:
            surface = self._ensure_progress()
            if surface is None:
                return
            surface.entrance_animation.stop()
            surface.rootObject().setProperty('entrance', 1.)
            surface.setPosition(*progress_position(self._original_area or Rect(0, 0, 800, 600), (272, 72)))
            surface.show()  # Establish a readable pill before hiding its wheel.
            self._changing_flags = True
            try:
                self.hide()
            finally:
                self._changing_flags = False

    def expand_progress(self):
        if self.state.stage not in ('converting', 'result'):
            return
        self._success_expiry_enabled = False  # Explicit detail viewing pauses expiry.
        self.success_timer.stop()
        self._cancel_progress_motion()
        self.session.presentation_state.expand()
        self.session.presentationChanged.emit()
        surface = self._ensure_progress()
        if surface is None:
            return
        surface.rootObject().setProperty('entrance', 1.)
        surface.setHeight(190)
        area = self._original_area or Rect(0, 0, 800, 600)
        surface.setPosition(*progress_position(area, (272, 190)))
        # Explicit click, unlike background updates, may focus details for Esc.
        surface.set_accepts_focus(True)
        surface.show()
        surface.requestActivate()
        surface.rootObject().forceActiveFocus()
        self._changing_flags = True
        try:
            self.hide()
        finally:
            self._changing_flags = False

    def completed_progress(self):
        self.collapse_progress()
        if self.session.presentation_state.mode == ProgressMode.SUCCEEDED:
            self._success_expiry_enabled = True
            self._arm(self.success_timer, 4500, self._expire_success, self._progress_serial)

    def _expire_success(self, generation=None, serial=None):
        generation = self._generation if generation is None else generation
        serial = self._progress_serial if serial is None else serial
        if (not self._current_progress(generation, serial) or self.job
                or self.session.presentation_state.mode != ProgressMode.SUCCEEDED
                or not self.session.presentation_state.compact):
            return
        if self.progress_view is None or self.session.reducedMotion or self.session.lowEffects:
            self._finish()
            return
        animation = self.progress_view.entrance_animation
        animation.stop()
        animation.setDuration(180)
        animation.setStartValue(1.)
        animation.setEndValue(0.)
        animation.start()
        self._arm(self.expiry_timer, 180, self._finish_expiry, serial)

    def _finish_expiry(self, generation=None, serial=None):
        generation = self._generation if generation is None else generation
        serial = self._progress_serial if serial is None else serial
        if (self._current_progress(generation, serial) and not self.job
                and self.session.presentation_state.mode == ProgressMode.SUCCEEDED
                and self.session.presentation_state.compact):
            self._finish()

    def dismiss_progress(self):
        if self.job:
            self.collapse_progress()
        else:
            self._finish()

    def reveal_output(self):
        result = self.session.conversion_result
        if not result or not result.outputs:
            return
        path = Path(result.outputs[0])
        if os.name == 'nt':
            import subprocess
            try:
                subprocess.Popen(['explorer.exe', '/select,', str(path)], shell=False)
            except OSError:
                self.show_details()
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))

    def show_details(self):
        from filewheel.converters.debugging import debug_log_path
        if self._details_box is not None:
            self._details_box.raise_()
            self._details_box.activateWindow()
            return
        box = QMessageBox()
        box.setWindowTitle('Filewheel conversion details')
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setText(self.session.statusTitle)
        box.setInformativeText(self.session.detail)
        box.setDetailedText('Local log: ' + str(debug_log_path()))
        self._details_box = box
        box.finished.connect(self._close_details)
        box.open()

    def _close_details(self):
        box, self._details_box = self._details_box, None
        if box is not None:
            box.deleteLater()

    def _hide_progress(self):
        self._cancel_progress_motion()
        if self.progress_view is not None and isValid(self.progress_view):
            self.progress_view.rootObject().setProperty('entrance', 1.)
            changing = self.progress_view._changing
            self.progress_view._changing = True
            try:
                self.progress_view.hide()  # Intentional reuse must not enqueue native-hide recovery.
            finally:
                self.progress_view._changing = changing

    def _finish(self):
        if self.job or self._finished:
            return
        self._finished = True  # Native hide/close can reenter during hide().
        self._success_expiry_enabled = False
        self._generation += 1
        self._cancel_selection_motion()
        self.focus_timer.stop()
        self.leave_timer.stop()
        self.tooltip_timer.stop()
        self.success_timer.stop()
        self.expiry_timer.stop()
        self.transition_timer.stop()
        self._hide_progress()
        self.hide()
        self.state.dismiss()
        self.session._refresh()
        self.finished.emit()

    def _dismiss_if_inactive(self, generation=None):
        if generation is not None and generation != self._generation:
            return
        if self.isVisible() and not self.isActive():
            self.collapse_progress() if self.persistent else self.dismiss()

    def _native_progress_hide(self, generation):
        if generation == self._generation and self.persistent and not self._finished:
            self.collapse_progress()

    def event(self, event):
        if hasattr(self, 'focus_timer') and not self._changing_flags:
            if event.type() in (QEvent.Type.FocusOut, QEvent.Type.WindowDeactivate):
                self._arm(self.focus_timer, 0, self._dismiss_if_inactive)
            elif event.type() == QEvent.Type.Leave:
                self.pointer_exited()
            elif event.type() == QEvent.Type.Hide:
                if self.persistent:
                    generation = self._generation
                    QTimer.singleShot(0, lambda: self._native_progress_hide(generation))
                else:
                    self._finish()
            elif event.type() == QEvent.Type.Close:
                self.collapse_progress() if self.persistent else self.dismiss()
                event.ignore()
                return True
        return super().event(event)


class ProgressSurface(QQuickView):
    """No-focus topmost informational surface; never owns or cancels a worker."""
    def __init__(self, owner):
        super().__init__()
        self.render_diagnostics = RenderDiagnostics(self, 'progress')
        self.owner = owner
        self.setTitle('Filewheel progress')
        owner.destroyed.connect(self.deleteLater)
        self._changing = False
        self.setColor(QColor('transparent'))
        self.set_accepts_focus(False)
        self.setWidth(272)
        self.setHeight(72)
        self.rootContext().setContextProperty('progress', owner.session)
        self.setSource(QUrl.fromLocalFile(str(Path(__file__).with_name('qml') / 'ProgressSurface.qml')))
        if self.status() == QQuickView.Status.Error:
            details = '; '.join(e.toString() for e in self.errors())
            self._changing = True
            self.setSource(QUrl())
            self.deleteLater()
            raise RuntimeError('Progress scene failed: ' + details)
        self.entrance_animation = QPropertyAnimation(self.rootObject(), b'entrance', self)
        self.entrance_animation.setDuration(210)
        self.entrance_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        if self.render_diagnostics.enabled:
            self.entrance_animation.stateChanged.connect(
                lambda new, old: self.render_diagnostics.snapshot('animation_' + new.name))

    def set_accepts_focus(self, accept):
        flags = (Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                 | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.NoDropShadowWindowHint)
        if not accept:
            flags |= Qt.WindowType.WindowDoesNotAcceptFocus
        if self.flags() == flags:
            return
        visible = self.isVisible()
        self._changing = True
        try:
            self.render_diagnostics.record('flags', old=int(self.flags()), new=int(flags))
            self.setFlags(flags)
            if visible:
                self.show()
        finally:
            self._changing = False

    def event(self, event):
        if hasattr(self, 'owner') and not self._changing:
            if event.type() == QEvent.Type.Close:
                self.owner.dismiss_progress()
                event.ignore()
                return True
            if event.type() == QEvent.Type.Hide and self.owner.persistent and not self.owner._closing and not self.owner._finished:
                generation, serial = self.owner._generation, self.owner._progress_serial
                QTimer.singleShot(0, lambda: self.owner._recover_progress(generation, serial))
        return super().event(event)
