import os
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import PureWindowsPath
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from filewheel.ui.desktop import DesktopApplication
    QT = True
except ImportError:
    QT = False
from filewheel.core.experimental import CandidateGate, ExperimentalCandidate
from filewheel.core.explicit_paths import FileCheck


class FakeRuntime:
    def __init__(self, candidate, error, *, allow_injected_candidates=False):
        self.allow_injected_candidates = allow_injected_candidates
        self.gate = CandidateGate()
        self.threads_alive = False
        self.running = False
    def start(self):
        self.running = True
        return True
    def close(self, **kwargs):
        self.running = False
        self.gate.cancel()
        return True


@unittest.skipUnless(QT, 'Qt optional')
class DesktopConsentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['consent-tests'])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {'FILEWHEEL_LOG_DIR': self.temp.name}); self.env.start()
        self.addCleanup(self.env.stop)
        self.inspections = []
        def inspect(path):
            self.inspections.append(path)
            return FileCheck(True, True)
        self.desktop = DesktopApplication(tray=True, runtime_factory=FakeRuntime,
                                          inspector=inspect, point_mapper=lambda p,s:p,
                                          confirm_candidates=True)

    def tearDown(self):
        self.desktop.request_quit()
        self.app.processEvents()
        self.desktop.popup.close()
        self.desktop.popup.deleteLater()
        self.desktop.deleteLater()
        self.app.processEvents()

    def enable(self):
        self.desktop.set_experiment(True)
        deadline = time.monotonic() + 2
        while self.desktop._startup is not None and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.assertIsNone(self.desktop._startup)

    def offer(self):
        self.enable()
        now = time.monotonic()
        candidate = ExperimentalCandidate(PureWindowsPath('C:/file.png'), (500, 300), now-.1, now)
        self.desktop.runtime.gate.offer(candidate)
        self.desktop.offer_candidate(candidate)
        self.app.processEvents()
        return candidate

    def test_disabled_by_default_no_listener_or_candidate_popup(self):
        self.assertIsNone(self.desktop.runtime)
        self.assertFalse(self.desktop.experimental_enabled)
        self.assertFalse(self.desktop.experiment_action.isChecked())
        self.assertEqual(self.inspections, [])

    def test_confirmation_precedes_validation_and_preserves_event_point(self):
        candidate = self.offer()
        self.assertIsNotNone(self.desktop.dialog)
        self.assertEqual(self.inspections, [])
        self.assertFalse(self.desktop.popup.isVisible())
        box = self.desktop.dialog
        self.assertNotEqual(box.defaultButton(), self.desktop.confirm_button)
        with patch.object(self.desktop.popup, 'present', return_value=True) as present:
            QTest.mouseClick(self.desktop.confirm_button, Qt.MouseButton.LeftButton)
            self.app.processEvents()
        self.assertEqual(len(self.inspections), 1)
        target = present.call_args.args[0]
        self.assertEqual(target.point, candidate.point)
        self.assertEqual(target.source, 'user_confirmed_candidate')

    def test_cancel_never_validates_or_opens_conversion_popup(self):
        self.offer()
        self.desktop.dialog.reject()
        self.app.processEvents()
        self.assertEqual(self.inspections, [])
        self.assertFalse(self.desktop.popup.isVisible())

    def test_superseded_confirmation_cannot_open_menu(self):
        self.offer()
        now = time.monotonic()
        self.desktop.runtime.gate.offer(ExperimentalCandidate(PureWindowsPath('C:/other.png'), (500,300), now-.1, now))
        with patch.object(self.desktop.popup, 'present') as present:
            QTest.mouseClick(self.desktop.confirm_button, Qt.MouseButton.LeftButton)
            self.app.processEvents()
        present.assert_not_called()
        self.assertEqual(self.inspections, [])

    def test_dead_worker_cleanup_warning_does_not_hang_quit(self):
        self.enable()
        self.desktop.runtime.close = lambda **kwargs: False
        self.desktop.runtime.threads_alive = False
        self.desktop.request_quit()
        self.assertIsNone(self.desktop.runtime)
        self.assertFalse(self.desktop.shutdown_timer.isActive())

    def test_listener_start_wait_does_not_block_qt_events(self):
        from threading import Event

        from PySide6.QtCore import QTimer
        released = Event()
        class SlowRuntime(FakeRuntime):
            def start(self):
                return released.wait(2)
        self.desktop.runtime_factory = SlowRuntime
        QTimer.singleShot(20, released.set)
        started = time.monotonic()
        self.desktop.set_experiment(True)
        self.assertLess(time.monotonic() - started, .2)
        deadline = time.monotonic() + 2
        while self.desktop._startup is not None and time.monotonic() < deadline:
            self.app.processEvents(); time.sleep(.005)
        self.assertTrue(released.is_set())
        self.assertIsNone(self.desktop._startup)

    def test_hook_failure_before_startup_finished_stays_disabled(self):
        class FailedAfterStart(FakeRuntime):
            def __init__(self, candidate, error, *, allow_injected_candidates=False):
                super().__init__(candidate, error, allow_injected_candidates=allow_injected_candidates)
                self.error = error
            def start(self):
                self.running = False
                self.error('mouse_hook: RuntimeError')
                return True
        self.desktop.runtime_factory = FailedAfterStart
        self.enable()
        self.app.processEvents()
        self.assertFalse(self.desktop.experimental_enabled)
        self.assertFalse(self.desktop.experiment_action.isChecked())

    def test_tray_action_stops_listener_and_resets_status_after_threads_exit(self):
        self.desktop.experiment_action.trigger()
        deadline = time.monotonic() + 2
        while self.desktop._startup is not None and time.monotonic() < deadline:
            self.app.processEvents(); time.sleep(.005)
        self.assertTrue(self.desktop.experimental_enabled)
        runtime = self.desktop.runtime
        runtime.threads_alive = True
        runtime.close = lambda **kwargs: False
        self.desktop.experiment_action.trigger()
        self.assertFalse(self.desktop.experimental_enabled)
        self.assertFalse(self.desktop.experiment_action.isChecked())
        self.assertFalse(self.desktop.experiment_action.isEnabled())
        self.assertIn('stopping', self.desktop.tray.toolTip())
        runtime.threads_alive = False
        self.desktop._poll_mouse_stop()
        self.assertIsNone(self.desktop.runtime)
        self.assertTrue(self.desktop.experiment_action.isEnabled())
        self.assertIn('off', self.desktop.tray.toolTip())
        self.assertFalse(self.desktop.stop_timer.isActive())

    def test_runtime_error_resets_active_tooltip(self):
        self.enable()
        self.desktop.mouse_error('hook failed')
        self.assertFalse(self.desktop.experimental_enabled)
        self.assertIn('off', self.desktop.tray.toolTip())

    def test_no_file_invocation_adopts_tray_without_enabling_experiment(self):
        self.desktop.tray_mode = False
        with patch('filewheel.ui.desktop.QSystemTrayIcon.isSystemTrayAvailable', return_value=True):
            self.assertTrue(self.desktop.ensure_tray())
        self.assertTrue(self.desktop.tray_mode)
        self.assertIsNone(self.desktop.runtime)
        self.assertFalse(self.desktop.experimental_enabled)
        self.desktop.quitting = True
        self.assertFalse(self.desktop.ensure_tray())

    def test_direct_open_revalidates_without_dialog_and_records_provisional_source(self):
        self.desktop.confirm_action.trigger()  # Opt out of per-file confirmation.
        with patch.object(self.desktop.popup, 'present', return_value=True) as present:
            candidate = self.offer()
        self.assertIsNone(self.desktop.dialog)
        self.assertEqual(len(self.inspections), 1)
        target = present.call_args.args[0]
        self.assertEqual(target.source, 'experimental_candidate')
        self.assertEqual(target.point, candidate.point)
        self.assertEqual(target.path, candidate.path)
        with patch.object(self.desktop.popup, 'present') as again:
            self.desktop.offer_candidate(candidate)
        again.assert_not_called()  # A consumed token cannot reopen.

    def test_direct_open_missing_file_never_presents(self):
        self.desktop.set_confirmation(False)
        self.desktop.inspector = lambda path: FileCheck(False, False)
        with patch.object(self.desktop.popup, 'present') as present:
            self.offer()
        present.assert_not_called()
        self.assertIsNone(self.desktop.dialog)

    def test_direct_open_is_default_for_new_host(self):
        host = DesktopApplication(point_mapper=lambda p, s: p)
        try:
            self.assertFalse(host.confirm_candidates)
            self.assertFalse(host.confirm_action.isChecked())
            self.assertIsNone(host.runtime)
        finally:
            host.popup.deleteLater()
            host.deleteLater()


    def offer_injected(self):
        self.desktop.set_confirmation(False)
        self.desktop.touchpad_action.trigger()
        self.enable()
        now = time.monotonic()
        candidate = ExperimentalCandidate(PureWindowsPath('C:/file.png'), (500, 300),
                                          now-.1, now, native_flags=1)
        self.desktop.runtime.gate.offer(candidate)
        self.desktop.offer_candidate(candidate)
        self.app.processEvents()
        return candidate

    def test_touchpad_is_opt_in_session_setting_and_locked_while_listening(self):
        self.assertFalse(self.desktop.allow_injected_candidates)
        self.assertFalse(self.desktop.touchpad_action.isChecked())
        self.desktop.touchpad_action.trigger()
        self.assertTrue(self.desktop.allow_injected_candidates)
        self.enable()
        self.assertTrue(self.desktop.runtime.allow_injected_candidates)
        self.assertFalse(self.desktop.touchpad_action.isEnabled())
        self.desktop.set_touchpad(False)  # Even programmatic changes cannot race a runtime.
        self.assertTrue(self.desktop.allow_injected_candidates)
        self.desktop.set_experiment(False)
        self.assertIsNone(self.desktop.runtime)
        self.assertTrue(self.desktop.touchpad_action.isEnabled())
        self.desktop.touchpad_action.trigger()
        self.assertFalse(self.desktop.allow_injected_candidates)

    def test_injected_candidate_always_confirms_even_when_physical_preference_is_off(self):
        with patch.object(self.desktop.popup, 'present', return_value=True) as present:
            candidate = self.offer_injected()
            present.assert_not_called()
            self.assertIsNotNone(self.desktop.dialog)
            self.assertEqual(self.inspections, [])
            self.assertEqual(self.desktop.dialog.informativeText(), str(candidate.path))
            self.assertNotEqual(self.desktop.dialog.defaultButton(), self.desktop.confirm_button)
            QTest.mouseClick(self.desktop.confirm_button, Qt.MouseButton.LeftButton)
            self.app.processEvents()
        self.assertEqual(len(self.inspections), 1)
        target = present.call_args.args[0]
        self.assertEqual(target.path, candidate.path)
        self.assertEqual(target.source, 'user_confirmed_candidate')
        self.assertEqual(target.point, candidate.point)

    def test_cancel_injected_confirmation_never_opens_or_inspects(self):
        with patch.object(self.desktop.popup, 'present') as present:
            self.offer_injected()
            self.desktop.dialog.reject()
            self.app.processEvents()
        present.assert_not_called()
        self.assertEqual(self.inspections, [])

    def test_injected_confirmation_deleted_file_rejects_at_controller(self):
        with patch.object(self.desktop.popup, 'present') as present:
            self.offer_injected()
            self.desktop.inspector = lambda path: FileCheck(False, False)
            QTest.mouseClick(self.desktop.confirm_button, Qt.MouseButton.LeftButton)
            self.app.processEvents()
        present.assert_not_called()

    def test_physical_candidate_keeps_direct_activation_with_touchpad_opt_in(self):
        self.desktop.set_confirmation(False)
        self.desktop.touchpad_action.trigger()
        with patch.object(self.desktop.popup, 'present', return_value=True) as present:
            candidate = self.offer()
        self.assertIsNone(self.desktop.dialog)
        self.assertFalse(candidate.requires_confirmation)
        self.assertEqual(present.call_args.args[0].source, 'experimental_candidate')

    def test_injected_queued_candidate_cannot_open_on_opt_out_host(self):
        self.desktop.set_confirmation(False)
        self.enable()
        now = time.monotonic()
        candidate = ExperimentalCandidate(PureWindowsPath('C:/file.png'), (500, 300), now-.1, now,
                                          native_flags=1)
        self.desktop.runtime.gate.offer(candidate)
        with patch.object(self.desktop.popup, 'present') as present:
            self.desktop.offer_candidate(candidate)
        self.assertIsNone(self.desktop.dialog)
        self.assertEqual(self.inspections, [])
        present.assert_not_called()

    def test_newer_candidate_invalidates_queued_injected_confirmation(self):
        with patch.object(self.desktop.popup, 'present') as present:
            candidate = self.offer_injected()
            self.desktop.runtime.gate.offer(replace(candidate, token='newer-token'))
            QTest.mouseClick(self.desktop.confirm_button, Qt.MouseButton.LeftButton)
            self.app.processEvents()
        present.assert_not_called()
        self.assertEqual(self.inspections, [])
