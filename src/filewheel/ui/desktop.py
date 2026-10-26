"""Resident tray host with direct or optionally confirmed experimental invocation."""
from time import monotonic

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from filewheel.converters import ConversionManager
from filewheel.converters.debugging import record_failure
from filewheel.core.controller import InvocationController
from filewheel.platforms.windows.explicit_path_diagnostics import inspect_file
from filewheel.ui.popup import RadialPopup


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
                 runtime_factory=None, point_mapper=None, confirm_candidates=False, parent=None):
        super().__init__(parent)
        self.manager = manager or ConversionManager()
        self.controller = InvocationController()
        self.inspector = inspector
        self.runtime_factory = runtime_factory
        self.runtime = None
        self._startup = None
        self.experimental_enabled = False
        self.dialog = None
        self.confirm_button = None
        self.confirm_candidates = bool(confirm_candidates)
        self.allow_injected_candidates = False  # Explicit, session-only touchpad opt-in.
        self.tray_mode = tray
        self.quitting = False
        self.bridge = _Bridge(self)
        self.bridge.candidate.connect(self.offer_candidate)
        self.bridge.error.connect(self.mouse_error)
        options = {'manager': self.manager}
        if point_mapper is not None:
            options['point_mapper'] = point_mapper
        self.popup = RadialPopup(self.manager.registry, **options)
        self.popup.finished.connect(self._popup_finished)
        self.tray = QSystemTrayIcon(self._icon(), self)
        self.menu = QMenu()
        self.experiment_action = QAction('Experimental Mouse3', self)
        self.experiment_action.setCheckable(True)
        self.experiment_action.toggled.connect(self.set_experiment)
        self.menu.addAction(self.experiment_action)
        self.touchpad_action = QAction('Touchpad middle-click (always confirm)', self)
        self.touchpad_action.setCheckable(True)
        self.touchpad_action.setToolTip('Allow injected gestures; turn Mouse3 off before changing.')
        self.touchpad_action.toggled.connect(self.set_touchpad)
        self.menu.addAction(self.touchpad_action)
        self.confirm_action = QAction('Confirm file before opening', self)
        self.confirm_action.setCheckable(True)
        self.confirm_action.setChecked(self.confirm_candidates)
        self.confirm_action.toggled.connect(self.set_confirmation)
        self.menu.addAction(self.confirm_action)
        quit_action = self.menu.addAction('Quit Filewheel')
        quit_action.triggered.connect(self.request_quit)
        self.tray.setContextMenu(self.menu)
        self.tray.setToolTip('Filewheel — Mouse3 experiment off')
        self.stop_timer = QTimer(self)
        self.stop_timer.setInterval(100)
        self.stop_timer.timeout.connect(self._poll_mouse_stop)
        self.shutdown_timer = QTimer(self)
        self.shutdown_timer.setInterval(100)
        self.shutdown_timer.timeout.connect(self._finish_quit)
        if tray:
            self.tray.show()

    def ensure_tray(self):
        """Adopt tray mode when a later no-file launch reaches a transient owner."""
        if self.quitting or not QSystemTrayIcon.isSystemTrayAvailable():
            return False
        self.tray_mode = True
        self.tray.show()
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

    def present_explicit(self, paths, point):
        if self.quitting or self.popup.job is not None:
            self.notify('A conversion is running; try again when it finishes.')
            return False
        self.close_confirmation()
        result = self.controller.handle_explicit(paths, point=point, timestamp=monotonic(),
                                                 inspect_file=self.inspector)
        if result.target is None:
            self.notify(f'Input rejected: {result.rejection}')
            return False
        return self._present(result.target)

    def _present(self, target):
        try:
            return self.popup.present(target)
        except (RuntimeError, OSError) as error:
            record_failure('desktop', 'present_popup', error)
            self.notify('Could not open the menu; see the local debug log.')
            return False

    @Slot(bool)
    def set_experiment(self, enabled):
        if self._startup is not None:
            self._check_action(False)
            return
        if enabled and not self.tray_mode:
            enabled = False
        self.close_confirmation()
        if self.runtime is not None:
            if not self.runtime.close(timeout=0):
                self.experimental_enabled = False
                self._check_action(False)
                self.experiment_action.setEnabled(False)
                self.touchpad_action.setEnabled(False)
                self.tray.setToolTip('Filewheel — Mouse3 stopping')
                self.stop_timer.start()
                return
            self.runtime = None
        self.experimental_enabled = False
        if enabled:
            factory = self.runtime_factory
            if factory is None:
                from filewheel.platforms.windows.mouse_runtime import MouseRuntime
                factory = MouseRuntime
            self.runtime = factory(self.bridge.candidate.emit, self.bridge.error.emit,
                                   allow_injected_candidates=self.allow_injected_candidates)
            self.touchpad_action.setEnabled(False)
            try:
                if hasattr(self.runtime, 'prepare'):
                    self.runtime.prepare()
            except (RuntimeError, OSError) as error:
                record_failure('mouse3', 'bootstrap', error)
                self._check_action(False)
                self.notify('Mouse3 COM bootstrap failed; see local diagnostics.')
                return
            self._startup = _StartMouse(self.runtime, self)
            self._startup.finished.connect(self._mouse_started)
            self.experiment_action.setEnabled(False)
            self._startup.start()
        self._check_action(self.experimental_enabled)
        if self.runtime is None:
            self.touchpad_action.setEnabled(not self.quitting)
        self.tray.setToolTip('Filewheel — Mouse3 experimental' if self.experimental_enabled
                             else 'Filewheel — Mouse3 experiment off')

    @Slot()
    def _poll_mouse_stop(self):
        if self.runtime is not None and self.runtime.threads_alive:
            return
        self.stop_timer.stop()
        self.runtime = None
        self.experiment_action.setEnabled(not self.quitting)
        self.touchpad_action.setEnabled(not self.quitting)
        self.tray.setToolTip('Filewheel — Mouse3 experiment off')

    @Slot()
    def _mouse_started(self):
        startup, self._startup = self._startup, None
        self.experimental_enabled = bool(startup.result and not self.quitting
                                         and self.runtime is not None and self.runtime.running)
        startup.deleteLater()
        self.experiment_action.setEnabled(True)
        self._check_action(self.experimental_enabled)
        self.tray.setToolTip('Filewheel — Mouse3 experimental' if self.experimental_enabled
                             else 'Filewheel — Mouse3 experiment off')
        if not self.experimental_enabled and not self.quitting:
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
        self.tray.setToolTip('Filewheel — Mouse3 experiment off')
        record_failure('mouse3', 'runtime', RuntimeError(message))
        self.notify(f'Mouse3 stopped: {message}. Send to remains available.')

    @Slot(bool)
    def set_touchpad(self, enabled):
        # A runtime's policy is immutable; don't leave an in-flight injected
        # candidate valid across a setting change. Stop Mouse3 before changing.
        if self.runtime is not None or self._startup is not None or self.quitting:
            self.touchpad_action.blockSignals(True)
            self.touchpad_action.setChecked(self.allow_injected_candidates)
            self.touchpad_action.blockSignals(False)
            return
        self.close_confirmation()
        self.allow_injected_candidates = enabled is True

    @Slot(bool)
    def set_confirmation(self, enabled):
        self.close_confirmation()
        self.confirm_candidates = bool(enabled)

    @Slot(object)
    def offer_candidate(self, candidate):
        if (not self.experimental_enabled or self.runtime is None or self.quitting
                or self.popup.job is not None
                or (candidate.requires_confirmation and not self.allow_injected_candidates)
                or not self.runtime.gate.is_current(candidate.token, now=monotonic())):
            return
        self.close_confirmation(cancel_gate=False)
        self.popup.dismiss()
        if not self.confirm_candidates and not candidate.requires_confirmation:
            result = self.runtime.gate.activate(candidate.token, self.controller, self.inspector,
                                                now=monotonic())
            if result.target is not None:
                self._present(result.target)
            else:
                self.notify(f'Candidate rejected: {result.rejection}')
            return
        box = QMessageBox()
        box.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setWindowTitle('Experimental Mouse3 — confirm proposed file')
        box.setText('Explorer mapping is provisional. Confirm this exact file before continuing.')
        box.setInformativeText(str(candidate.path))
        box.setDetailedText('This is an experimental index correlation, not a verified hover identity.\n'
                            'Cancel if the proposed path is not the file you intended.'
                            + ('\nInjected middle-clicks always require confirmation; the hook flags '
                               'do not identify a touchpad.' if candidate.requires_confirmation else ''))
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
        elif not self.tray_mode and self.dialog is None:
            QApplication.instance().quit()

    @Slot()
    def request_quit(self):
        self.quitting = True
        self.stop_timer.stop()
        self.experiment_action.setEnabled(False)
        self.touchpad_action.setEnabled(False)
        self.experimental_enabled = False
        self.close_confirmation()
        self.controller.cancel()
        self.popup.dismiss()
        if self.runtime is not None:
            self.runtime.close(timeout=0)
        self.shutdown_timer.start()
        self._finish_quit()

    def _finish_quit(self):
        if self.popup.job is not None or self._startup is not None:
            return
        if self.runtime is not None and not self.runtime.close(timeout=0):
            if self.runtime.threads_alive:
                return
            record_failure('mouse3', 'shutdown_cleanup', RuntimeError('Worker cleanup failed after threads stopped'))
            self.runtime = None
        self.shutdown_timer.stop()
        self.tray.hide()
        QApplication.instance().quit()
