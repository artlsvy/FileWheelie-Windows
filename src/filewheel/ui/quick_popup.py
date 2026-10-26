"""Optional scenegraph popup. Controller DTOs and conversion jobs stay unchanged."""
import math
import os
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

from filewheel.converters.base import ConversionCancelled, ConversionError
from filewheel.converters.debugging import describe_conversion_error, error_details, record_failure
from filewheel.performance import get_recorder
from filewheel.ui.conversion_controller import ConversionController
from filewheel.ui.desktop_errors import DesktopInitializationError
from filewheel.ui.placement import Rect, popup_position
from filewheel.ui.popup import logical_point
from filewheel.ui.progress_state import ProgressMode, ProgressPresentation, progress_position
from filewheel.ui.quick_geometry import SIZE, hit_test, inside_boundary
from filewheel.ui.radial import DEFAULT_PREVIEW_REGISTRY, RadialState


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
        if self.stage == 'result' and index == -2:
            self.view.tooltip_timer.start()
        else:
            self.view.tooltip_timer.stop()
            QToolTip.hideText()

    @Slot()
    def clearHover(self):
        self.view.pointer_boundary(-1, -1)
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
            self.view.mark_pending('choose_to_paint')
            self._refresh()
        else:
            self.view.dismiss()

    def choose(self, index):
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

    def __init__(self, registry=DEFAULT_PREVIEW_REGISTRY, *, point_mapper=logical_point,
                 manager=None, source_mapper=lambda path: Path(str(path)), coordinator=None, _scene_file=None):
        QQuickWindow.setDefaultAlphaBuffer(True)
        super().__init__()
        self.point_mapper = point_mapper
        self.coordinator = coordinator or ConversionController(QApplication.instance())
        self.progress_view = None
        self._transitioning = False
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
        self.focus_timer.timeout.connect(self._dismiss_if_inactive)
        self.leave_timer = QTimer(self)
        self.leave_timer.setSingleShot(True)
        self.leave_timer.setInterval(75)
        self.leave_timer.timeout.connect(self._dismiss_if_outside)
        self.tooltip_timer = QTimer(self)
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.setInterval(450)
        self.tooltip_timer.timeout.connect(lambda: QToolTip.showText(QCursor.pos(), '<pre>' + escape(self.session.detail) + '</pre>'))
        self.transition_timer = QTimer(self)
        self.transition_timer.setSingleShot(True)
        self.transition_timer.timeout.connect(self._finish_collapse)
        self.success_timer = QTimer(self)
        self.success_timer.setSingleShot(True)
        self.success_timer.setInterval(4500)
        self.success_timer.timeout.connect(self._expire_success)
        self.expiry_timer = QTimer(self)
        self.expiry_timer.setSingleShot(True)
        self.expiry_timer.timeout.connect(self._finish_expiry)
        self.position_animation = None

    @property
    def state(self):
        return self.session.state

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
        # MouseArea's rectangle includes transparent corners. Test the actual
        # circle even when the hovered sector remains -1. Do not restart an
        # active debounce for every outside move or dismissal could starve.
        if self.state.stage == 'converting' and not inside_boundary(x, y):
            self.collapse_progress()
            return
        if self.state.stage not in ('categories', 'formats') or inside_boundary(x, y):
            self.leave_timer.stop()
        elif self.isVisible() and not self.leave_timer.isActive():
            self.leave_timer.start()

    def _dismiss_if_outside(self):
        if not self.isVisible() or self.state.stage not in ('categories', 'formats'):
            return
        # Recheck the current logical cursor after the debounce. Mapping via
        # QWindow avoids applying one DPR to global/mixed-monitor coordinates.
        local = self.mapFromGlobal(QCursor.pos())
        if not inside_boundary(local.x(), local.y()):
            self.dismiss()

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
        self.leave_timer.stop()
        self.success_timer.stop()
        self.expiry_timer.stop()
        self.transition_timer.stop()
        self._hide_progress()
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
        self.mark_pending('present_to_paint')
        self.show()
        self.raise_()
        self.requestActivate()
        self.rootObject().forceActiveFocus()
        self.update()
        return True

    def set_persistent(self, enabled):
        if enabled and hasattr(self, 'leave_timer'):
            self.leave_timer.stop()
        kind = Qt.WindowType.Tool if enabled else Qt.WindowType.Popup
        flags = (kind | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                 | Qt.WindowType.NoDropShadowWindowHint)
        if self.flags() == flags:
            return
        visible = self.isVisible()
        self._changing_flags = True
        try:
            self.setFlags(flags)
            if visible and not self.isVisible():
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

    def _ensure_progress(self):
        if self.progress_view is None:
            try:
                self.progress_view = ProgressSurface(self)
            except (ImportError, RuntimeError, OSError) as error:
                record_failure('quick', 'create_progress_surface', error)
                self.session.presentation_state.expand()
                self.session.presentationChanged.emit()
                self.rootObject().setProperty('collapsing', False)
                self.set_persistent(True)
                self.show()  # Retain observable full status without cancelling work.
                return None
        return self.progress_view

    def collapse_progress(self):
        if self.state.stage not in ('converting', 'result') or self._closing:
            return
        surface = self._ensure_progress()
        if surface is None:
            return
        if self._transitioning:
            return
        was_visible = surface.isVisible()
        old_position = surface.position()
        self.session.presentation_state.collapse()
        self.session.presentationChanged.emit()
        surface.set_accepts_focus(False)
        surface.setHeight(72)
        area = self._original_area or Rect(0, 0, 800, 600)
        destination = QPoint(*progress_position(area, (272, 72)))
        reduced = self.session.reducedMotion or self.session.lowEffects
        if surface.isVisible() and not self.isVisible() and surface.height() == 72:
            surface.setPosition(destination)
            return
        if surface.screen() != self.screen():
            surface.setScreen(self.screen())
        start = old_position if was_visible else self.position() + QPoint(-16, 84)
        surface.setPosition(destination if reduced else start)
        surface.show()  # Tool + WindowDoesNotAcceptFocus: never activate here.
        self.rootObject().setProperty('collapsing', True)
        self._transitioning = not reduced
        if reduced:
            self._finish_collapse()
        else:
            surface.rootObject().setProperty('entrance', 0.)
            if self.position_animation is not None:
                self.position_animation.stop()
                self.position_animation.deleteLater()
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
            self.transition_timer.start(210)

    def _finish_collapse(self):
        self._transitioning = False
        if self.session.presentation_state.compact and self.persistent:
            self._changing_flags = True
            try:
                self.hide()
            finally:
                self._changing_flags = False

    def expand_progress(self):
        if self.state.stage not in ('converting', 'result'):
            return
        self.success_timer.stop()
        self.expiry_timer.stop()
        self.transition_timer.stop()
        self._transitioning = False
        if self.position_animation is not None:
            self.position_animation.stop()
        self.session.presentation_state.expand()
        self.session.presentationChanged.emit()
        surface = self._ensure_progress()
        if surface is None:
            return
        surface.entrance_animation.stop()
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
            self.success_timer.start()

    def _expire_success(self):
        if self.job or self.session.presentation_state.mode != ProgressMode.SUCCEEDED:
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
        self.expiry_timer.start(180)

    def _finish_expiry(self):
        if not self.job and self.session.presentation_state.mode == ProgressMode.SUCCEEDED:
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
        box = QMessageBox()
        box.setWindowTitle('Filewheel conversion details')
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setText(self.session.statusTitle)
        box.setInformativeText(self.session.detail)
        box.setDetailedText('Local log: ' + str(debug_log_path()))
        box.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._details_box = box
        box.open()

    def _hide_progress(self):
        if self.position_animation is not None:
            self.position_animation.stop()
        self._transitioning = False
        if self.progress_view is not None:
            self.progress_view.entrance_animation.stop()
            self.progress_view.rootObject().setProperty('entrance', 1.)
            self.progress_view.hide()


    def _finish(self):
        if self.job or self._finished:
            return
        self._finished = True  # Native hide/close can reenter during hide().
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

    def _dismiss_if_inactive(self):
        if self.isVisible() and not self.isActive():
            self.collapse_progress() if self.persistent else self.dismiss()

    def event(self, event):
        if hasattr(self, 'focus_timer') and not self._changing_flags:
            if event.type() in (QEvent.Type.FocusOut, QEvent.Type.WindowDeactivate):
                self.focus_timer.start(0)
            elif event.type() == QEvent.Type.Leave:
                self.pointer_boundary(-1, -1)
            elif event.type() == QEvent.Type.Hide:
                if self.persistent:
                    QTimer.singleShot(0, self.collapse_progress)
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
        self.owner = owner
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

    def set_accepts_focus(self, accept):
        visible = self.isVisible()
        self._changing = True
        try:
            flags = (Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                     | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.NoDropShadowWindowHint)
            if not accept:
                flags |= Qt.WindowType.WindowDoesNotAcceptFocus
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
                QTimer.singleShot(0, self._restore)
        return super().event(event)

    def _restore(self):
        if self.owner.persistent and not self.owner._closing and not self.owner._finished:
            self.show()
