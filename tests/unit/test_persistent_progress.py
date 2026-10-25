"""Qt worker/visibility semantics; native Windows z-order still needs acceptance."""
import os
import time
import unittest
from pathlib import Path, PureWindowsPath
from threading import Event
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtCore import QEvent, QPoint, Qt
    from PySide6.QtGui import QFocusEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QWidget

    from filewheel.ui.popup import RadialPopup
    QT = True
except ImportError:
    QT = False

from filewheel.converters.base import ConversionCancelled, ConversionError, ConversionResult
from filewheel.core.models import TargetResolution
from filewheel.ui.radial import DEFAULT_PREVIEW_REGISTRY


class BlockingManager:
    registry = DEFAULT_PREVIEW_REGISTRY

    def __init__(self, fail=False):
        self.release = Event()
        self.started = Event()
        self.fail = fail

    def convert(self, source, extension, *, progress, cancel):
        progress(.42, 'engine parser internal operation: very verbose diagnostic message')
        self.started.set()
        while not self.release.wait(.005):
            if cancel.is_set():
                raise ConversionCancelled('Engine cleanup complete')
        if self.fail:
            raise ConversionError('Detailed backend failure; private filename and native operation')
        return ConversionResult((Path('/tmp/converted-output.jpg'),), ('Detailed engine warning',), 'test')


@unittest.skipUnless(QT, 'PySide6 required')
class PersistentProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['persistent-status-tests'])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.manager = BlockingManager()
        self.popup = RadialPopup(self.manager.registry, manager=self.manager,
                                point_mapper=lambda point, screens: point)
        self.other = QWidget()
        self.finished = []
        self.popup.finished.connect(lambda: self.finished.append(True))
        self.target = TargetResolution(PureWindowsPath('C:/fixture/long source filename.png'),
                                       0, (400, 300), 1, 'shell_explicit')
        self.popup.present(self.target)

    def wait(self, predicate):
        deadline = time.monotonic() + 3
        while not predicate() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.assertTrue(predicate())

    def tearDown(self):
        self.manager.release.set()
        self.popup.dismiss()
        self.wait(lambda: self.popup.job is None)
        self.other.close()
        self.popup.deleteLater()
        self.other.deleteLater()
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def start(self):
        self.popup._choose(0)
        self.popup._choose(0)
        self.wait(lambda: self.manager.started.is_set() and self.popup.progress_fraction == .42)

    def outside_activity(self):
        self.other.show()
        self.other.activateWindow()
        QTest.mouseClick(self.other, Qt.MouseButton.LeftButton)
        self.app.sendEvent(self.popup, QFocusEvent(QEvent.Type.FocusOut))
        self.app.sendEvent(self.popup, QEvent(QEvent.Type.WindowDeactivate))
        with patch.object(self.popup, 'isActiveWindow', return_value=False):
            self.popup._dismiss_if_inactive()
        QTest.mouseClick(self.popup, Qt.MouseButton.LeftButton, pos=QPoint(1, 1))
        self.app.processEvents()

    def drawn_text(self):
        texts = []
        original = self.popup._text
        def capture(painter, rect, text, *args, **kwargs):
            texts.append(text)
            return original(painter, rect, text, *args, **kwargs)
        with patch.object(self.popup, '_text', new=capture):
            image = self.popup.grab().toImage()
        self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
        return texts

    def test_topmost_tool_transition_preserves_geometry_worker_and_visible_result(self):
        geometry = self.popup.geometry()
        self.popup._focus_check.start(0)  # A queued menu focus check must not close progress.
        self.start()
        self.assertEqual(self.popup.windowType(), Qt.WindowType.Tool)
        self.assertTrue(self.popup.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        self.assertEqual(self.popup.geometry(), geometry)
        self.assertFalse(self.popup.job.cancelled.is_set())
        self.assertEqual(self.finished, [])
        self.outside_activity()
        self.assertTrue(self.popup.isVisible())
        self.assertFalse(self.popup.job.cancelled.is_set())
        self.assertEqual(self.drawn_text(), ['In progress', '42%', 'Cancel'])
        self.manager.release.set()
        self.wait(lambda: self.popup.job is None)
        self.outside_activity()
        self.assertEqual(self.popup.state.stage, 'result')
        self.assertTrue(self.popup.isVisible())
        self.assertEqual(self.popup.windowType(), Qt.WindowType.Tool)
        self.assertEqual(self.drawn_text(), ['Done', 'File saved', 'Done'])
        self.assertIn('converted-output.jpg', self.popup.toolTip())
        self.assertIn('Detailed engine warning', self.popup.toolTip())
        center = self.popup._action_rect().center() * self.popup._scale
        QTest.mouseClick(self.popup, Qt.MouseButton.LeftButton, pos=center.toPoint())
        self.assertFalse(self.popup.isVisible())
        self.assertEqual(self.finished, [True])
        self.popup.present(self.target)
        self.assertEqual(self.popup.windowType(), Qt.WindowType.Popup)
        self.assertFalse(self.popup.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating))
        self.assertTrue(self.popup.isVisible())

    def test_cancel_and_escape_keep_status_until_worker_acknowledges(self):
        for escape in (False, True):
            with self.subTest(escape=escape):
                self.manager = BlockingManager()
                self.popup.manager = self.manager
                self.popup.present(self.target)
                self.start()
                if escape:
                    QTest.keyClick(self.popup, Qt.Key.Key_Escape)
                else:
                    center = self.popup._action_rect().center() * self.popup._scale
                    QTest.mouseClick(self.popup, Qt.MouseButton.LeftButton, pos=center.toPoint())
                self.assertTrue(self.popup.isVisible())
                self.assertFalse(self.popup._closing)
                self.wait(lambda: self.popup.job is None)
                self.assertEqual(self.popup.last_selection.action, 'conversion_cancelled')
                self.assertTrue(self.popup.isVisible())
                self.assertEqual(self.drawn_text(), ['Cancelled', '', 'Done'])

    def test_error_is_simple_but_details_remain_available(self):
        self.manager.fail = True
        self.start()
        self.manager.release.set()
        self.wait(lambda: self.popup.job is None)
        self.outside_activity()
        self.assertEqual(self.drawn_text(), ['Failed', 'Hover for details', 'Done'])
        self.assertIn('Detailed backend failure', self.popup.toolTip())
        self.assertIn('long source filename.png', self.popup.toolTip())
        self.assertEqual(self.popup.last_selection.action, 'conversion_failed')

    def test_programmatic_dismiss_still_cancels_and_finishes_exactly_once(self):
        self.start()
        self.popup.dismiss()
        self.assertFalse(self.popup.isVisible())
        self.wait(lambda: self.popup.job is None)
        self.assertEqual(self.finished, [True])
        self.assertEqual(self.popup.last_selection.action, 'conversion_cancelled')

    def test_busy_invocation_rejects_without_cancelling_existing_conversion(self):
        self.start()
        self.assertFalse(self.popup.present(self.target))
        self.assertFalse(self.popup.job.cancelled.is_set())
        self.assertTrue(self.popup.isVisible())
