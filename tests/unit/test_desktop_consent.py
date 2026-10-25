import os
import tempfile
import time
import unittest
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
    def __init__(self, candidate, error):
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
                                          inspector=inspect, point_mapper=lambda p,s:p)

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
