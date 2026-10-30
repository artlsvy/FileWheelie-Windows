"""Resident tray host with direct or optionally confirmed experimental invocation."""
from dataclasses import replace
from time import monotonic

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QColorDialog, QMenu, QMessageBox, QSystemTrayIcon

from filewheel import preferences
from filewheel.converters import ConversionManager
from filewheel.converters.debugging import record_failure
from filewheel.core.controller import InvocationController
from filewheel.performance import get_recorder
from filewheel.platforms.services import inspect_file, path_flavour, startup
from filewheel.ui.backend import create_popup
from filewheel.ui.conversion_controller import ConversionController


class _Bridge(QObject):
    candidate = Signal(object)
    error = Signal(str)


class _StartMouse(QThread):
    def __init__(self, runtime, parent):
        super().__init__(parent)
        self.runtime = runtime
        self.result = False

    def run(self):
        try:
            self.result = self.runtime.start()
        except Exception as error:  # noqa: BLE001 - thread startup boundary
            record_failure("mouse3", "startup", error)


class DesktopApplication(QObject):
    def __init__(self, *, tray=False, manager=None, inspector=inspect_file,
                 runtime_factory=None, point_mapper=None, confirm_candidates=False, ui_backend=None,
                 auto_start=False, parent=None):
        super().__init__(parent)
        timing = get_recorder()
        started = monotonic() if timing.enabled else None
        self.manager = manager or ConversionManager()
        if started is not None:
            timing.record('registry_startup', (monotonic() - started) * 1000)
        self.controller = InvocationController(path_flavour=path_flavour())
        self.login_startup = startup()
        self.inspector = inspector
        self.runtime_factory = runtime_factory
        self.runtime = None
        self.extra_resources = []
        self.linux_bridge = None
        self._startup = None
        self.experimental_enabled = False
        self.dialog = None
        self.confirm_button = None
        self.confirm_candidates = bool(confirm_candidates)
        self.allow_injected_candidates = True
        self.accent_color = preferences.accent_color()
        self.color_dialog = None
        self.auto_start = auto_start
        self.tray_mode = tray
        self.quitting = False
        self.bridge = _Bridge(self)
        self.bridge.candidate.connect(self.offer_candidate)
        self.bridge.error.connect(self.mouse_error)
        self.conversions = ConversionController(self)
        options = {'manager': self.manager, 'coordinator': self.conversions}
        if point_mapper is not None:
            options['point_mapper'] = point_mapper
        self.popup = create_popup(self.manager.registry, backend=ui_backend, **options)
        self.popup.set_accent_color(self.accent_color)
        self.popup.finished.connect(self._popup_finished)
        self.tray = QSystemTrayIcon(self._icon(), self)
        self.menu = QMenu()
        self.experiment_action = QAction('Enable wheel', self)
        self.experiment_action.setCheckable(True)
        self.experiment_action.toggled.connect(self.set_experiment)
        self.menu.addAction(self.experiment_action)
        self.login_action = QAction('Start on login', self)
        self.login_action.setCheckable(True)
        self.login_action.toggled.connect(self.set_start_on_login)
        self.menu.addAction(self.login_action)
        self.accent_action = self.menu.addAction('Accent color…')
        self.accent_action.triggered.connect(self.choose_accent_color)
        self.reset_accent_action = self.menu.addAction('Reset accent color')
        self.reset_accent_action.setEnabled(self.accent_color is not None)
        self.reset_accent_action.triggered.connect(lambda: self.set_accent_color(None))
        self.menu.aboutToShow.connect(self._refresh_login)
        self._refresh_login()
        diagnostics = getattr(self.popup, 'render_diagnostics', None)
        if diagnostics is not None and diagnostics.enabled:
            trace_action = self.menu.addAction('Save UI trace snapshot')
            trace_action.triggered.connect(self.popup._trace_presentation)
        self.menu.addSeparator()
        quit_action = self.menu.addAction('Quit Filewheel')
        quit_action.triggered.connect(self.request_quit)
        self.tray.setContextMenu(self.menu)
        self.tray.setToolTip('Filewheel — wheel disabled')
        self.stop_timer = QTimer(self)
        self.stop_timer.setInterval(100)
        self.stop_timer.timeout.connect(self._poll_mouse_stop)
        self.shutdown_timer = QTimer(self)
        self.shutdown_timer.setInterval(100)
        self.shutdown_timer.timeout.connect(self._finish_quit)
        if tray:
            self.tray.show()
            if self.auto_start:
                QTimer.singleShot(0, self._start_default_wheel)

    def _start_default_wheel(self):
        if not self.quitting and preferences.wheel_enabled():
            self.set_experiment(True, persist=False)

    @Slot()
    def choose_accent_color(self):
        if self.quitting:
            return
        if self.color_dialog is not None:
            self.color_dialog.raise_()
            self.color_dialog.activateWindow()
            return
        dialog = QColorDialog(QColor(self.accent_color or '#173E32'))
        dialog.setWindowTitle('Filewheel — accent color')
        dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
        self.color_dialog = dialog
        # Release any selection popup before opening a conventional dialog.
        # Active conversions keep running and collapse to their progress pill.
        self.popup.dismiss()
        dialog.colorSelected.connect(lambda color: self.set_accent_color(color.name()))
        dialog.finished.connect(self._close_color_dialog)
        dialog.open()

    def _close_color_dialog(self):
        dialog, self.color_dialog = self.color_dialog, None
        if dialog is not None:
            dialog.deleteLater()

    def set_accent_color(self, color):
        if self.quitting:
            return
        try:
            preferences.save_accent_color(color)
        except (OSError, ValueError) as error:
            record_failure('desktop', 'save_accent_color', error)
            self.notify('Could not save the accent color. Your previous color is unchanged.')
            return
        self.accent_color = preferences.accent_color()
        self.popup.set_accent_color(self.accent_color)
        self.reset_accent_action.setEnabled(self.accent_color is not None)

    def _refresh_login(self):
        self.login_action.blockSignals(True)
        try:
            self.login_action.setChecked(self.login_startup.is_enabled())
        except (OSError, RuntimeError):
            self.login_action.setChecked(False)
        finally:
            self.login_action.blockSignals(False)

    @Slot(bool)
    def set_start_on_login(self, enabled):
        try:
            self.login_startup.configure('install' if enabled else 'remove')
        except (OSError, RuntimeError) as error:
            record_failure('desktop', 'start_on_login', error)
            self.notify('Could not change Start on login. An entry from another installation is preserved.')
        self._refresh_login()

    def ensure_tray(self):
        """Adopt tray mode when a later no-file launch reaches a transient owner."""
        if self.quitting or not QSystemTrayIcon.isSystemTrayAvailable():
            return False
        was_transient = not self.tray_mode
        self.tray_mode = True
        self.tray.show()
        if was_transient and self.auto_start:
            QTimer.singleShot(0, self._start_default_wheel)
        return True

    @staticmethod
    def _icon():
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor('#173e32')); painter.setPen(QColor('#f5efdf'))
        painter.drawEllipse(2, 2, 28, 28)
        painter.drawText(pixmap.rect(), 0x84, 'F')
        painter.end()
        return QIcon(pixmap)

    def notify(self, message):
        if self.tray_mode:
            self.tray.showMessage('Filewheel', message)

    def present_explicit(self, paths, point, *, source=None):
        if QApplication.activeModalWidget() is not None:
            self.notify('Close the open dialog before selecting another file.')
            return False
        if self.quitting or self.popup.job is not None:
            self.notify('A conversion is running; try again when it finishes.')
            return False
        self.close_confirmation()
        result = self.controller.handle_explicit(paths, point=point, timestamp=monotonic(),
                                                 inspect_file=self.inspector)
        if result.target is None:
            self.notify(f'Input rejected: {result.rejection}')
            return False
        target=result.target
        if source is not None:
            if path_flavour()!='posix' or source!='dolphin_click':
                raise ValueError('Invalid Linux bridge provenance')
            target=replace(target,source=source)
        return self._present(target)

    def _present(self, target):
        try:
            return self.popup.present(target)
        except (RuntimeError, OSError) as error:
            record_failure('desktop', 'present_popup', error)
            self.notify('Could not open the menu; see the local debug log.')
            return False

    @Slot(bool)
    def set_experiment(self, enabled, *, persist=True):
        if self.quitting:
            return
        if self.linux_bridge is not None:
            self.linux_bridge.enabled = bool(enabled)
            self.experimental_enabled = bool(enabled)
            self._check_action(bool(enabled))
            self.tray.setToolTip('Filewheel — private Dolphin bridge '+('enabled' if enabled else 'disabled'))
            if persist:
                try:
                    preferences.save_wheel_enabled(enabled)
                except OSError as error:
                    record_failure('desktop','save_preferences',error)
            if not enabled and self.popup.job is None:
                self.popup.dismiss()
            return
        if self._startup is not None:
            self._check_action(False)
            return
        if enabled and not self.tray_mode:
            enabled = False
        if persist:
            try:
                preferences.save_wheel_enabled(enabled)
            except (OSError, KeyError) as error:
                record_failure('desktop', 'save_preferences', error)
                self.notify('Wheel changed for this session; could not save the preference.')
        self.close_confirmation()
        if not enabled and self.popup.job is None:
            self.popup.dismiss()
        if self.runtime is not None:
            if not self.runtime.close(timeout=0):
                self.experimental_enabled = False
                self._check_action(False)
                self.experiment_action.setEnabled(False)
                self.tray.setToolTip('Filewheel — wheel stopping')
                self.stop_timer.start()
                return
            self.runtime = None
        self.stop_timer.stop()
        self.experimental_enabled = False
        if enabled:
            factory = self.runtime_factory
            if factory is None and path_flavour() == 'posix':
                self._check_action(False)
                self.notify('Linux middle-click requires the opt-in private Dolphin bridge.')
                return
            if factory is None:
                from filewheel.platforms.windows.mouse_runtime import MouseRuntime
                factory = MouseRuntime
            try:
                self.runtime = factory(self.bridge.candidate.emit, self.bridge.error.emit,
                                       allow_injected_candidates=self.allow_injected_candidates)
                if hasattr(self.runtime, 'prepare'):
                    self.runtime.prepare()
            except (RuntimeError, OSError) as error:
                record_failure('mouse3', 'bootstrap', error)
                if self.runtime is not None:
                    self.runtime.close(timeout=0)
                self.experiment_action.setEnabled(False)
                self.stop_timer.start()
                self._check_action(False)
                self.notify('Mouse3 COM bootstrap failed; see local diagnostics.')
                return
            self._startup = _StartMouse(self.runtime, self)
            self._startup.finished.connect(self._mouse_started)
            self.experiment_action.setEnabled(False)
            self._startup.start()
        self._check_action(self.experimental_enabled)
        self.tray.setToolTip('Filewheel — wheel enabled' if self.experimental_enabled
                             else 'Filewheel — wheel disabled')

    @Slot()
    def _poll_mouse_stop(self):
        if self._startup is not None:
            return
        if self.runtime is not None and self.runtime.threads_alive:
            return
        self.stop_timer.stop()
        self.runtime = None
        self.experiment_action.setEnabled(not self.quitting)
        self.tray.setToolTip('Filewheel — wheel disabled')

    @Slot()
    def _mouse_started(self):
        startup, self._startup = self._startup, None
        self.experimental_enabled = bool(startup.result and not self.quitting
                                         and self.runtime is not None and self.runtime.running)
        startup.deleteLater()
        self.experiment_action.setEnabled(not self.quitting)
        self._check_action(self.experimental_enabled)
        self.tray.setToolTip('Filewheel — wheel enabled' if self.experimental_enabled
                             else 'Filewheel — wheel disabled')
        if not self.experimental_enabled and not self.quitting:
            if self.runtime is not None:
                self.runtime.close(timeout=0)
            self.experiment_action.setEnabled(False)
            self.stop_timer.start()  # Release a failed runtime before policy changes.
            self.notify('Mouse3 could not start; see local diagnostics.')
        if self.quitting:
            self._finish_quit()

    def _check_action(self, checked):
        self.experiment_action.blockSignals(True)
        self.experiment_action.setChecked(checked)
        self.experiment_action.blockSignals(False)

    @Slot(str)
    def mouse_error(self, message):
        self.experimental_enabled = False
        self._check_action(False)
        self.close_confirmation()
        self.tray.setToolTip('Filewheel — wheel disabled')
        if self.runtime is not None:
            self.runtime.close(timeout=0)
            self.experiment_action.setEnabled(False)
            self.stop_timer.start()
        record_failure('mouse3', 'runtime', RuntimeError(message))
        self.notify(f'Mouse3 stopped: {message}. Send to remains available.')

    @Slot(bool)
    def set_confirmation(self, enabled):
        self.close_confirmation()
        self.confirm_candidates = bool(enabled)

    @Slot(object)
    def offer_candidate(self, candidate):
        if (not self.experimental_enabled or self.runtime is None or self.quitting
                or QApplication.activeModalWidget() is not None
                or self.popup.job is not None
                or (candidate.is_injected and not self.allow_injected_candidates)
                or not self.runtime.gate.is_current(candidate.token, now=monotonic())):
            return
        timing = get_recorder()
        if timing.enabled:
            timing.record('candidate_to_ui', (monotonic() - candidate.captured_at) * 1000)
        self.close_confirmation(cancel_gate=False)
        self.popup.dismiss()
        if not self.confirm_candidates:
            result = self.runtime.gate.activate(candidate.token, self.controller, self.inspector,
                                                now=monotonic())
            if result.target is not None:
                shown = self._present(result.target)
                if shown and timing.enabled:
                    timing.record('candidate_to_show', (monotonic() - candidate.captured_at) * 1000)
            else:
                self.notify(f'Candidate rejected: {result.rejection}')
            return
        box = QMessageBox()
        box.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setWindowTitle('Filewheel — confirm file')
        box.setText('Open the conversion menu for this file?')
        box.setInformativeText(str(candidate.path))
        box.setDetailedText('Cancel if this is not the file you intended.')
        yes = box.addButton('Use this file', QMessageBox.ButtonRole.AcceptRole)
        cancel = box.addButton(QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(cancel)
        self.dialog, self.confirm_button = box, yes
        timer = QTimer(box)
        timer.setSingleShot(True)
        timer.timeout.connect(box.reject)
        timer.start(30_000)
        box._deadline = timer
        box.finished.connect(lambda result: self._confirmed(box, yes, candidate))
        box.open()
        box.raise_()
        box.activateWindow()

    def _confirmed(self, box, yes, candidate):
        if self.dialog is not box:
            return
        self.dialog = None
        self.confirm_button = None
        box._deadline.stop()
        if box.clickedButton() is yes and self.experimental_enabled and not self.quitting:
            result = self.runtime.gate.confirm(candidate.token, self.controller, self.inspector,
                                               now=monotonic())
            if result.target is not None:
                self._present(result.target)
            else:
                self.notify(f'Candidate rejected after confirmation: {result.rejection}')
        elif self.runtime is not None:
            self.runtime.gate.cancel()
        box.deleteLater()

    def close_confirmation(self, *, cancel_gate=True):
        box, self.dialog = self.dialog, None
        self.confirm_button = None
        if box is not None:
            box._deadline.stop(); box.reject(); box.deleteLater()
        if cancel_gate and self.runtime is not None:
            self.runtime.gate.cancel()

    def _popup_finished(self):
        if self.quitting:
            self._finish_quit()
        elif not self.tray_mode and self.dialog is None and self.color_dialog is None:
            QApplication.instance().quit()

    @Slot()
    def request_quit(self):
        self.quitting = True
        if self.color_dialog is not None:
            self.color_dialog.reject()
        self.stop_timer.stop()
        self.experiment_action.setEnabled(False)
        self.login_action.setEnabled(False)
        self.experimental_enabled = False
        self.close_confirmation()
        self.controller.cancel()
        self.popup.shutdown()
        if self.runtime is not None:
            self.runtime.close(timeout=0)
        self.shutdown_timer.start()
        self._finish_quit()

    def _finish_quit(self):
        if self.popup.job is not None or self._startup is not None:
            return
        if any(not resource.close(timeout=0) for resource in self.extra_resources):
            return
        if self.runtime is not None and not self.runtime.close(timeout=0):
            if self.runtime.threads_alive:
                return
            record_failure('mouse3', 'shutdown_cleanup', RuntimeError('Worker cleanup failed after threads stopped'))
            self.runtime = None
        self.shutdown_timer.stop()
        self.tray.hide()
        QApplication.instance().quit()
