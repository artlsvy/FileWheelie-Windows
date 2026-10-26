"""Scaled offscreen interaction, alpha compositing and conversion outcome feedback."""

import os
import time
import unittest
from pathlib import Path, PureWindowsPath
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtCore import QEvent, QPoint, QRect, Qt
    from PySide6.QtGui import QFont, QFontMetrics
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from filewheel.ui.popup import RadialPopup

    AVAILABLE = True
except ImportError:
    AVAILABLE = False

from filewheel.converters.base import ConversionCancelled, ConversionError, ConversionResult
from filewheel.core.models import TargetResolution
from filewheel.ui.radial import DEFAULT_PREVIEW_REGISTRY


def target():
    return TargetResolution(
        PureWindowsPath("C:/fixtures/Résumé very long filename.png"),
        0,
        (350, 300),
        1.0,
        "shell_explicit",
    )


@unittest.skipUnless(AVAILABLE, "Optional PySide6 required for offscreen polish tests")
class UiPolishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["filewheel-polish-tests"])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.popup = RadialPopup(point_mapper=lambda point, screens: point)
        self.popup.present(target())

    def tearDown(self):
        self.popup.close()
        self.app.processEvents()
        self.popup.deleteLater()
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def point(self, x, y):
        return QPoint(round(x * self.popup.width() / 324), round(y * self.popup.height() / 324))

    def choose_preview(self):
        QTest.mouseClick(self.popup, Qt.MouseButton.LeftButton, pos=self.point(267, 162))
        QTest.mouseClick(self.popup, Qt.MouseButton.LeftButton, pos=self.point(253, 110))
        self.assertEqual(self.popup.state.stage, "confirmation")

    def test_default_and_configurable_diameter(self):
        self.assertEqual((self.popup.width(), self.popup.height()), (170, 170))
        for diameter in (170, 190, 220, 260, 324):
            popup = RadialPopup(diameter=diameter)
            self.assertEqual(popup.width(), diameter)
            popup.deleteLater()
        for diameter in (169, 325, 240.0, True):
            with self.assertRaises(ValueError):
                RadialPopup(diameter=diameter)

    def test_scaled_category_format_center_back_and_escape(self):
        QTest.mouseClick(self.popup, Qt.MouseButton.LeftButton, pos=self.point(267, 162))
        self.assertEqual(self.popup.state.stage, "formats")
        QTest.mouseClick(self.popup, Qt.MouseButton.LeftButton, pos=self.point(162, 162))
        self.assertEqual(self.popup.state.stage, "categories")
        self.choose_preview()
        self.assertEqual(self.popup.last_selection.output_extension, ".jpg")
        QTest.keyClick(self.popup, Qt.Key.Key_Escape)
        self.assertFalse(self.popup.isVisible())

    def test_corners_remain_transparent_after_state_changes(self):
        for change in (lambda: None, self.choose_preview):
            change()
            self.app.processEvents()
            image = self.popup.grab().toImage()
            edge = self.popup.width() - 1
            for x, y in ((0, 0), (edge, 0), (0, edge), (edge, edge), (4, 4)):
                self.assertEqual(image.pixelColor(x, y).alpha(), 0)
        self.assertTrue(self.popup.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertFalse(self.popup.autoFillBackground())
        self.assertTrue(self.popup.windowFlags() & Qt.WindowType.NoDropShadowWindowHint)

    def test_full_source_tooltip_and_scaled_outside_right_click(self):
        QTest.mouseMove(self.popup, self.point(162, 162))
        self.assertIn("Résumé very long filename.png", self.popup.toolTip())
        QTest.mouseClick(self.popup, Qt.MouseButton.RightButton, pos=QPoint(1, 1))
        self.assertFalse(self.popup.isVisible())

    def test_failure_and_cancel_have_real_outcome_even_when_closed(self):
        for error, action, title in (
            (ConversionError("Broken document"), "conversion_failed", "Conversion failed"),
            (ConversionCancelled("Stopped"), "conversion_cancelled", "Cancelled"),
        ):
            self.popup.present(target())
            self.choose_preview()
            fake_job = Mock()
            self.popup.job = fake_job
            self.popup._closing = True
            self.popup._conversion_done(None, error)
            # Presenter receives only a stopped-worker outcome; joining/deletion
            # belongs to ConversionController, never a GUI callback.
            fake_job.wait.assert_not_called()
            fake_job.deleteLater.assert_not_called()
            self.assertEqual(self.popup.last_selection.action, action)
            self.assertEqual(self.popup.last_selection.outputs, ())
            self.assertEqual(self.popup.status_title, title)
            self.assertIs(self.popup.conversion_error, error)
            self.assertTrue(self.popup._finished)

    def test_multi_output_success_metadata_and_warning_tooltip(self):
        self.choose_preview()
        result = ConversionResult(
            (Path("/tmp/page-001.png"), Path("/tmp/page-002.png")),
            ("Rasterized pages", "No editable text"),
            "test",
        )
        self.popup.job = Mock()
        self.popup._conversion_done(result, None)
        self.assertEqual(self.popup.last_selection.action, "converted")
        self.assertEqual(self.popup.last_selection.outputs, result.outputs)
        self.assertEqual(self.popup.conversion_result, result)
        self.assertIn("+1 files", self.popup.status_message)
        for detail in ("page-001.png", "page-002.png", "Rasterized pages", "No editable text"):
            self.assertIn(detail, self.popup.toolTip())

    def test_actual_worker_cancel_updates_metadata_before_finished(self):
        class Manager:
            def convert(self, source, extension, *, progress, cancel):
                progress(0.25, "Waiting for cancellation")
                if cancel.wait(2):
                    raise ConversionCancelled("Stopped before publication")
                raise ConversionError("Cancellation was not received")

        self.popup.close()
        self.popup.deleteLater()
        self.popup = RadialPopup(
            DEFAULT_PREVIEW_REGISTRY, manager=Manager(), point_mapper=lambda point, screens: point
        )
        self.popup.present(target())
        outcomes = []
        self.popup.finished.connect(lambda: outcomes.append(self.popup.last_selection.action))
        self.popup._choose(0)
        self.popup._choose(0)
        self.assertEqual(self.popup.last_selection.action, "conversion_started")
        self.popup.shutdown()  # Explicit shutdown cancels; dismiss now preserves work.
        deadline = time.monotonic() + 3
        while self.popup.job is not None and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.002)
        self.assertIsNone(self.popup.job)
        self.assertEqual(outcomes, ["conversion_cancelled"])
        self.assertFalse(self.popup.isVisible())


    def test_category_center_is_escape_and_formats_center_is_back(self):
        QTest.mouseClick(self.popup, Qt.MouseButton.LeftButton, pos=self.point(162, 162))
        self.assertFalse(self.popup.isVisible())
        self.popup.present(target())
        self.popup._choose(0)
        QTest.mouseClick(self.popup, Qt.MouseButton.LeftButton, pos=self.point(162, 162))
        self.assertEqual(self.popup.state.stage, "categories")
        self.assertTrue(self.popup.isVisible())

    def test_conversion_result_and_preview_share_circular_alpha_and_button_hits(self):
        for stage in ("confirmation", "converting", "result"):
            with self.subTest(stage=stage):
                self.popup.present(target())
                self.choose_preview()
                self.popup.state.stage = stage
                self.popup.status_title = "Converting" if stage == "converting" else "Converted"
                self.popup.status_message = "A lengthy explanatory message kept inside the circle"
                self.popup.progress_fraction = .5
                image = self.popup.grab().toImage()
                # This point was inside the former rounded rectangular status card.
                transparent = self.point(24, 60)
                self.assertEqual(image.pixelColor(transparent).alpha(), 0)
                self.assertGreater(image.pixelColor(self.point(162, 22)).alpha(), 0)
                self.assertEqual(self.popup._hit(self.point(162, 265)), -2)
                self.assertEqual(self.popup._hit(self.point(60, 265)), -1)
                QTest.mouseClick(self.popup, Qt.MouseButton.LeftButton, pos=self.point(162, 265))
                self.assertEqual(self.popup.isVisible(), stage == "converting")

    def test_circle_outside_point_keeps_conversion_visible(self):
        self.choose_preview()
        self.popup.state.stage = "converting"
        QTest.mouseClick(self.popup, Qt.MouseButton.LeftButton, pos=self.point(24, 60))
        self.assertTrue(self.popup.isVisible())

    def test_compact_long_category_labels_fit_without_unbroken_word_overflow(self):
        font = QFont("Segoe UI")
        font.setPointSizeF(9.5 / self.popup._scale)
        font.setBold(True)
        metrics = QFontMetrics(font)
        for label in ("Document", "Markdown\nText"):
            with self.subTest(label=label):
                wrapped = self.popup._wrap_long_words(label, metrics, 110)
                bounds = metrics.boundingRect(QRect(0, 0, 110, 104),
                                              Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                                              wrapped)
                self.assertLessEqual(bounds.width(), 110)
                self.assertLessEqual(bounds.height(), 104)
                self.assertEqual(wrapped.replace("\n", ""), label.replace("\n", ""))

    def test_compact_size_preserves_action_hit_regions(self):
        self.choose_preview()
        self.assertEqual(self.popup.width(), 170)
        action = self.popup._action_rect()
        center = action.center()
        self.assertEqual(self.popup._hit(self.point(center.x(), center.y())), -2)
        self.assertEqual(self.popup._hit(self.point(24, 60)), -1)
