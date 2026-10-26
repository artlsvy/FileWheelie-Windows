"""Optional scenegraph popup. Controller DTOs and conversion jobs stay unchanged."""
import math
import os
from dataclasses import replace
from html import escape
from pathlib import Path
from threading import Lock
from time import monotonic

from PySide6.QtCore import Property, QEvent, QObject, QPoint, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QCursor
from PySide6.QtQuick import QQuickView, QQuickWindow
from PySide6.QtWidgets import QApplication, QToolTip

from filewheel.converters.base import ConversionCancelled, ConversionError
from filewheel.converters.debugging import describe_conversion_error, error_details
from filewheel.performance import get_recorder
from filewheel.ui.conversion_job import ConversionJob
from filewheel.ui.desktop_errors import DesktopInitializationError
from filewheel.ui.placement import Rect, popup_position
from filewheel.ui.popup import logical_point
from filewheel.ui.quick_geometry import SIZE, hit_test
from filewheel.ui.radial import DEFAULT_PREVIEW_REGISTRY, RadialState


class GlassSession(QObject):
    """Small Qt bridge over the existing navigation state and production worker."""
    optionsChanged = Signal()
    hoverChanged = Signal()
    stageChanged = Signal()
    statusChanged = Signal()
    appearanceChanged = Signal()

    def __init__(self, view, registry, manager, source_mapper):
        super().__init__(view)
        self.view = view
        self.state = RadialState(registry)
        self.manager, self.source_mapper = manager, source_mapper
        self.job = None
        self.last_selection = self.conversion_result = self.conversion_error = None
        self._hovered = self._keyboard = -1
        self._progress = 0.
        self._status = self._detail = ''
        self._dark = QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
        self._reduced = os.getenv('FILEWHEEL_REDUCED_MOTION') == '1'
        self._low = os.getenv('FILEWHEEL_LOW_EFFECTS') == '1'
        self._moving = True
        QApplication.styleHints().colorSchemeChanged.connect(self._sync_scheme)

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
        elif hit == -1 and not self.view.persistent:
            self.view.dismiss()

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
            self._status, self._detail, self._progress = 'In progress', '', 0.
            self.last_selection = replace(selection, action='conversion_started')
            self.view.set_persistent(True)
            self.job = ConversionJob(self.manager, self.source_mapper(selection.input_path),
                                     selection.output_extension, self)
            self.job.progress_changed.connect(self._conversion_progress)
            self.job.outcome.connect(self._conversion_done)
            self._refresh()
            self.job.start()
        self.view.selected.emit(self.last_selection)

    def request_cancel(self):
        if self.job:
            self.job.cancelled.set()
            self._status = 'Stopping'
            self.statusChanged.emit()

    def _conversion_progress(self, value, message):
        self._progress = max(0., min(1., value)) if math.isfinite(value) else 0.
        self._detail = message
        self.statusChanged.emit()

    def _conversion_done(self, result, error):
        job, self.job = self.job, None
        if job:
            job.wait()
            job.deleteLater()
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
        self._refresh()
        if self.view._closing:
            self.view._finish()


class GlassPopup(QQuickView):
    """Experimental selectable renderer; same present/finished/job desktop seam."""
    selected = Signal(object)
    finished = Signal()

    def __init__(self, registry=DEFAULT_PREVIEW_REGISTRY, *, point_mapper=logical_point,
                 manager=None, source_mapper=lambda path: Path(str(path)), _scene_file=None):
        QQuickWindow.setDefaultAlphaBuffer(True)
        super().__init__()
        self.point_mapper = point_mapper
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
        self.tooltip_timer = QTimer(self)
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.setInterval(450)
        self.tooltip_timer.timeout.connect(lambda: QToolTip.showText(QCursor.pos(), '<pre>' + escape(self.session.detail) + '</pre>'))

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
        if self.job:
            self._closing = True
            self.session.request_cancel()
        else:
            self._finish()

    def _finish(self):
        if self.job or self._finished:
            return
        self._finished = True  # Native hide/close can reenter during hide().
        self.focus_timer.stop()
        self.tooltip_timer.stop()
        self.hide()
        self.state.dismiss()
        self.session._refresh()
        self.finished.emit()

    def _dismiss_if_inactive(self):
        if self.isVisible() and not self.isActive() and not self.persistent:
            self.dismiss()

    def event(self, event):
        if hasattr(self, 'focus_timer') and not self._changing_flags:
            if event.type() in (QEvent.Type.FocusOut, QEvent.Type.WindowDeactivate):
                if not self.persistent:
                    self.focus_timer.start(0)
            elif event.type() == QEvent.Type.Hide and not self.persistent:
                self._finish()
            elif event.type() == QEvent.Type.Close:
                self.dismiss()
                event.ignore()
                return True
        return super().event(event)
