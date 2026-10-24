import os
import unittest
from unittest.mock import patch
from pathlib import PureWindowsPath

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtCore import QEvent, QPoint, QPointF, Qt, QTimer
    from PySide6.QtGui import QFocusEvent, QMouseEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from filewheel.ui.popup import RadialPopup, run_popup
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False

from filewheel.core.models import TargetResolution


def target(name="image.png"):
    return TargetResolution(PureWindowsPath("C:/fixtures") / name, 0, (400, 350), 1.0, "shell_explicit")


@unittest.skipUnless(QT_AVAILABLE, "PySide6 optional dependency unavailable")
class RadialPopupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["filewheel-tests"])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.popup = RadialPopup(point_mapper=lambda point, screens: point)
        self.popup.present(target())

    def tearDown(self):
        self.popup.close()
        self.app.processEvents()
        self.popup.deleteLater()
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def test_category_format_confirmation_and_done(self):
        self.app.processEvents()
        QTest.mouseClick(self.popup, Qt.MouseButton.LeftButton, pos=QPoint(267, 162))
        self.assertEqual(self.popup.state.stage, "formats")
        QTest.mouseClick(self.popup, Qt.MouseButton.LeftButton, pos=QPoint(253, 110))
        self.assertEqual(self.popup.state.stage, "confirmation")
        self.assertEqual(self.popup.last_selection.output_extension, ".jpg")
        # Offscreen paint really executes, including confirmation rendering.
        self.assertFalse(self.popup.grab().isNull())
        QTest.mouseClick(self.popup, Qt.MouseButton.LeftButton, pos=QPoint(162, 268))
        self.assertFalse(self.popup.isVisible())
        self.assertFalse(self.popup._animation.isActive())

    def test_center_back_escape_and_reopen(self):
        self.popup._choose(0)
        QTest.mouseClick(self.popup, Qt.MouseButton.LeftButton, pos=QPoint(162, 162))
        self.assertEqual(self.popup.state.stage, "categories")
        QTest.keyClick(self.popup, Qt.Key.Key_Escape)
        self.assertFalse(self.popup.isVisible())
        self.popup.present(target("new.docx"))
        self.assertEqual(self.popup.state.stage, "categories")
        self.assertEqual(self.popup.state.target.path.name, "new.docx")
        self.assertIsNone(self.popup.last_selection)

    def test_transparent_outside_corner_dismisses(self):
        QTest.mouseClick(self.popup, Qt.MouseButton.LeftButton, pos=QPoint(2, 2))
        self.assertFalse(self.popup.isVisible())

    def test_focus_loss_dismisses(self):
        with patch.object(self.popup, "isActiveWindow", return_value=False):
            self.app.sendEvent(self.popup, QFocusEvent(QEvent.Type.FocusOut))
            self.app.processEvents()
        self.assertFalse(self.popup.isVisible())

    def test_none_never_opens_and_invalid_gap_no_action(self):
        self.assertEqual(self.popup._hit(QPointF(162, 20)), -1)
        QTest.mouseClick(self.popup, Qt.MouseButton.LeftButton, pos=QPoint(162, 20))
        self.assertEqual(self.popup.state.stage, "categories")
        self.assertFalse(self.popup.present(None))
        self.assertFalse(self.popup.isVisible())
        self.assertIsNone(run_popup(None))

    def test_keyboard_and_hover(self):
        QTest.mouseMove(self.popup, QPoint(265, 162))
        self.assertEqual(self.popup.hovered, 0)
        QTest.keyClick(self.popup, Qt.Key.Key_Tab)
        QTest.keyClick(self.popup, Qt.Key.Key_Return)
        self.assertEqual(self.popup.state.stage, "formats")
        QTest.keyClick(self.popup, Qt.Key.Key_Backspace)
        self.assertEqual(self.popup.state.stage, "categories")

    def test_run_popup_event_loop_returns_selection_and_cleans_widgets(self):
        self.popup.close()
        self.app.processEvents()
        previous = self.app.quitOnLastWindowClosed()
        def confirm_and_close():
            popups = [widget for widget in self.app.topLevelWidgets()
                      if isinstance(widget, RadialPopup) and widget.isVisible()]
            self.assertEqual(len(popups), 1)
            popup = popups[0]
            popup._choose(0)
            popup._choose(0)
            popup.dismiss()
        QTimer.singleShot(0, confirm_and_close)
        result = run_popup(target())
        self.assertEqual(result.output_extension, ".jpg")
        self.assertEqual(self.app.quitOnLastWindowClosed(), previous)
        self.assertFalse(any(isinstance(widget, RadialPopup) and widget.isVisible()
                             for widget in self.app.topLevelWidgets()))

    def test_nonleft_outside_dismisses_but_inner_click_cannot_choose(self):
        QTest.mouseClick(self.popup, Qt.MouseButton.RightButton, pos=QPoint(267, 162))
        self.assertEqual(self.popup.state.stage, "categories")
        QTest.mouseClick(self.popup, Qt.MouseButton.RightButton, pos=QPoint(2, 2))
        self.assertFalse(self.popup.isVisible())

    def test_invalid_replacement_finishes_live_invocation_once(self):
        finished = []
        self.popup.finished.connect(lambda: finished.append(True))
        self.assertFalse(self.popup.present(None))
        self.assertEqual(len(finished), 1)
        self.assertTrue(self.popup._finished)
        self.assertFalse(self.popup.isVisible())
        self.assertEqual(self.popup.state.stage, "closed")
        self.popup.close()
        self.assertFalse(self.popup.present(None))
        self.assertEqual(len(finished), 1)

    def test_mapping_failure_replacement_finishes_live_invocation_once(self):
        finished = []
        self.popup.finished.connect(lambda: finished.append(True))
        def fail_mapping(point, screens):
            raise RuntimeError("monitor unavailable")
        self.popup.point_mapper = fail_mapping
        with self.assertRaisesRegex(RuntimeError, "monitor unavailable"):
            self.popup.present(target("replacement.docx"))
        self.assertEqual(len(finished), 1)
        self.assertTrue(self.popup._finished)
        self.assertFalse(self.popup.isVisible())
        self.assertEqual(self.popup.state.stage, "closed")
        self.popup.close()
        self.assertEqual(len(finished), 1)
