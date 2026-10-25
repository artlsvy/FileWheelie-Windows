"""Single annular boundaries share geometry between painting and hit testing."""

import math
import os
import unittest
from pathlib import PureWindowsPath
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QPainter as RealPainter
    from PySide6.QtWidgets import QApplication

    from filewheel.ui import popup as popup_module
    from filewheel.ui.popup import RadialPopup, radial_hit, radial_separators

    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False

from filewheel.core.models import TargetResolution
from filewheel.ui.radial import CapabilityRegistry, PreviewCapability


@unittest.skipUnless(QT_AVAILABLE, "PySide6 required for shared radial geometry tests")
class RadialBoundaryGeometryTests(unittest.TestCase):
    def test_each_boundary_is_one_unique_annular_segment(self):
        for count in (1, 2, 3):
            with self.subTest(count=count):
                segments = radial_separators(count)
                self.assertEqual(len(segments), 0 if count == 1 else count)
                normalized = {
                    tuple(round(value, 5) for point in line for value in point) for line in segments
                }
                self.assertEqual(len(normalized), len(segments))
                for start, end in segments:
                    self.assertAlmostEqual(math.dist(start, (162, 162)), 67)
                    self.assertAlmostEqual(math.dist(end, (162, 162)), 148)

    def test_single_separator_hit_width_matches_drawn_stroke(self):
        for count in (2, 3):
            for start, end in radial_separators(count):
                middle = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
                self.assertEqual(radial_hit(middle, count), -1)
                dx, dy = end[0] - start[0], end[1] - start[1]
                length = math.hypot(dx, dy)
                for side in (-1, 1):
                    near = (middle[0] + side * (-dy) / length, middle[1] + side * dx / length)
                    self.assertIn(radial_hit(near, count), range(count))
        self.assertEqual(radial_hit((162, 20), 1), 0)
        self.assertEqual(radial_hit((162, 162), 3), -2)
        self.assertEqual(radial_hit((1, 1), 3), -1)

    def test_hover_fill_paths_cover_annulus_without_center_or_overlap(self):
        for count in (1, 2, 3):
            paths = [
                popup_module._annular_sector(-90 + index * 360 / count, 360 / count)
                for index in range(count)
            ]
            self.assertTrue(all(not path.contains(QPointF(162, 162)) for path in paths))
            for index in range(count):
                angle = math.radians(-90 + (index + 0.5) * 360 / count)
                point = QPointF(162 + 105 * math.cos(angle), 162 + 105 * math.sin(angle))
                self.assertEqual(sum(path.contains(point) for path in paths), 1)
                self.assertTrue(paths[index].contains(point))


@unittest.skipUnless(QT_AVAILABLE, "PySide6 required for offscreen boundary checks")
class RadialBoundaryPaintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["boundary-tests"])
        cls.app.setQuitOnLastWindowClosed(False)

    def make_popup(self, count):
        registry = CapabilityRegistry(
            tuple(
                PreviewCapability(".png", "Image", extension, label)
                for extension, label in ((".jpg", "JPEG"), (".webp", "WebP"), (".tiff", "TIFF"))[
                    :count
                ]
            )
        )
        popup = RadialPopup(registry, point_mapper=lambda point, screens: point)
        popup.present(
            TargetResolution(
                PureWindowsPath("C:/fixture/input.png"), 0, (350, 300), 1, "shell_explicit"
            )
        )
        popup._choose(0)
        self.app.processEvents()
        return popup

    def dispose(self, popup):
        popup.close()
        popup.deleteLater()
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def test_painter_strokes_circles_and_each_separator_only_once(self):
        for count in (1, 2, 3):
            with self.subTest(count=count):
                popup = self.make_popup(count)
                events = []

                class TrackingPainter:
                    recorded_events = events
                    testcase = self
                    CompositionMode = RealPainter.CompositionMode
                    RenderHint = RealPainter.RenderHint

                    def __init__(self, widget):
                        self.actual = RealPainter(widget)

                    def __getattr__(self, name):
                        return getattr(self.actual, name)

                    def drawEllipse(self, rectangle):
                        if self.actual.pen().style() != Qt.PenStyle.NoPen:
                            self.recorded_events.append(
                                (
                                    "circle",
                                    (
                                        rectangle.x(),
                                        rectangle.y(),
                                        rectangle.width(),
                                        rectangle.height(),
                                    ),
                                )
                            )
                        self.actual.drawEllipse(rectangle)

                    def drawLine(self, start, end):
                        self.recorded_events.append(
                            ("separator", (start.x(), start.y(), end.x(), end.y()))
                        )
                        self.actual.drawLine(start, end)

                    def drawPath(self, path):
                        self.testcase.assertEqual(self.actual.pen().style(), Qt.PenStyle.NoPen)
                        self.actual.drawPath(path)

                    def __del__(self):
                        self.actual.end()

                try:
                    popup._hover_amounts = [1.0] + [0.0] * (count - 1)
                    with patch.object(popup_module, "QPainter", TrackingPainter):
                        self.assertFalse(popup.grab().isNull())
                    circles = [geometry for kind, geometry in events if kind == "circle"]
                    separators = [geometry for kind, geometry in events if kind == "separator"]
                    self.assertEqual(circles, [(14, 14, 296, 296), (95, 95, 134, 134)])
                    self.assertEqual(len(separators), 0 if count == 1 else count)
                    self.assertEqual(len(set(separators)), len(separators))
                finally:
                    self.dispose(popup)

    def test_rendered_separator_is_one_thin_band_without_parallel_outlines(self):
        for count in (1, 2, 3):
            with self.subTest(count=count):
                popup = self.make_popup(count)
                try:
                    image = popup.grab().toImage()
                    base = popup._colors()[0].lightnessF()
                    # Scan the top annular region, away from labels/circle edges.
                    dark = [
                        x
                        for x in range(114, 127)
                        if image.pixelColor(x, 32).lightnessF() < base - 0.012
                    ]
                    if count == 1:
                        self.assertEqual(dark, [])
                    else:
                        self.assertGreaterEqual(len(dark), 1)
                        self.assertLessEqual(len(dark), 2)
                        self.assertEqual(dark, list(range(min(dark), max(dark) + 1)))
                    self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
                    self.assertEqual(image.pixelColor(239, 239).alpha(), 0)
                    scaled_top = QPointF(162 * popup._scale, 20 * popup._scale)
                    self.assertEqual(popup._hit(scaled_top), 0 if count == 1 else -1)
                finally:
                    self.dispose(popup)
