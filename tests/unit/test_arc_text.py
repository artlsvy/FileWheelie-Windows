"""Curved labels and translucent surfaces retain readable, bounded geometry."""
import math
import os
import unittest
from pathlib import PureWindowsPath
from unittest.mock import patch

from filewheel.core.models import TargetResolution
from filewheel.ui.arc_text import arc_direction, arc_glyphs
from filewheel.ui.radial import CapabilityRegistry
from filewheel.ui.theme import DARK, LIGHT, contrast_ratio

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QColor, QPalette
    from PySide6.QtWidgets import QApplication

    from filewheel.ui import popup as module
    QT = True
except ImportError:
    QT = False


class ArcGeometryTests(unittest.TestCase):
    def test_upper_and_lower_arcs_read_left_to_right_with_upright_middle_glyph(self):
        for angle in (-90, 90):
            with self.subTest(angle=angle):
                glyphs = arc_glyphs('PNG', [10, 10, 10], angle, 100)
                self.assertEqual([g.text for g in glyphs], list('PNG'))
                self.assertLess(glyphs[0].x, glyphs[-1].x)
                self.assertAlmostEqual(glyphs[1].rotation, 0)
                for glyph in glyphs:
                    self.assertAlmostEqual(math.hypot(glyph.x - 162, glyph.y - 162), 100)
        self.assertEqual(arc_direction(-90), 1)
        self.assertEqual(arc_direction(90), -1)

    def test_measured_advances_control_angular_spacing_and_tangent_rotations(self):
        glyphs = arc_glyphs('AB', [10, 30], -90, 100)
        angles = [math.degrees(math.atan2(g.y - 162, g.x - 162)) for g in glyphs]
        self.assertAlmostEqual(angles[1] - angles[0], math.degrees(20 / 100))
        self.assertAlmostEqual(glyphs[0].rotation, angles[0] + 90)
        self.assertAlmostEqual(glyphs[1].rotation, angles[1] + 90)

    def test_invalid_geometry_rejects_instead_of_painting_nonfinite_coordinates(self):
        for radius, angle, advances in ((0, 0, [10]), (float('nan'), 0, [10]),
                                         (100, float('inf'), [10]), (100, 0, [-1]),
                                         (100, 0, [float('nan')]), (100, 0, [])):
            with self.subTest(radius=radius, angle=angle), self.assertRaises(ValueError):
                arc_glyphs('A', advances, angle, radius)

    def test_opaque_text_stays_readable_over_translucent_surface_extreme_backdrops(self):
        for theme in (LIGHT, DARK):
            for background in ('#000000', '#FFFFFF'):
                for surface in (theme.surface, theme.hover):
                    composed = '#' + ''.join(f'{round(int(surface[i:i+2],16)*235/255 + int(background[i:i+2],16)*20/255):02x}'
                                             for i in (1, 3, 5))
                    with self.subTest(surface=surface, background=background):
                        self.assertGreaterEqual(contrast_ratio(theme.text, composed), 4.5)
                        self.assertGreaterEqual(contrast_ratio(theme.outline, composed), 3)
                        if surface == theme.surface:
                            for text in (theme.muted, theme.accent, theme.error):
                                self.assertGreaterEqual(contrast_ratio(text, composed), 4.5)


@unittest.skipUnless(QT, 'PySide6 required')
class ArcSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['curved-label-tests'])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.popup = module.RadialPopup(point_mapper=lambda point, screens: point)
        self.target = TargetResolution(PureWindowsPath('C:/fixture/photo.png'), 0,
                                       (350, 300), 1, 'shell_explicit')
        self.popup.present(self.target)

    def tearDown(self):
        self.popup.close()
        self.popup.deleteLater()
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def test_normal_and_hovered_surfaces_remain_translucent_without_fading_whole_window(self):
        for dark in (False, True):
            palette = QPalette()
            palette.setColor(QPalette.ColorRole.Window, QColor('#111111' if dark else '#FFFFFF'))
            self.popup.setPalette(palette)
            for hover in (0., 1.):
                self.popup._hover_amounts = [hover] * len(self.popup.state.options)
                image = self.popup.grab().toImage()
                self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
                # Inside a sector, away from glyphs, separators and circle borders.
                point = (round(220 * self.popup._scale), round(110 * self.popup._scale))
                alpha = image.pixelColor(*point).alpha()
                self.assertGreaterEqual(alpha, 235)
                self.assertLess(alpha, 250)
                self.assertEqual(self.popup.windowOpacity(), 1.)

    def test_real_labels_follow_measured_arcs_and_fit_their_sector(self):
        original = module.arc_glyphs
        records = []
        def capture(text, advances, angle, radius):
            records.append((text, sum(advances), angle, radius))
            return original(text, advances, angle, radius)
        with patch.object(module, 'arc_glyphs', new=capture):
            self.popup.grab()
        self.assertEqual(len(records), len(self.popup.state.options))
        for text, width, angle, radius in records:
            self.assertTrue(text)
            self.assertLessEqual(width, radius * math.radians(140) + 1)
            self.assertIn(arc_direction(angle), (-1, 1))

    def test_no_formats_is_short_and_full_path_tooltip_survives(self):
        self.popup.state.registry = CapabilityRegistry(())
        self.popup.state.open(self.target)
        texts = []
        original = self.popup._text
        def capture(painter, rect, text, *args, **kwargs):
            texts.append(text)
            return original(painter, rect, text, *args, **kwargs)
        with patch.object(self.popup, '_text', new=capture):
            self.popup.grab()
        self.assertIn('No formats', texts)
        self.assertNotIn('No available formats', texts)
        self.assertIn(str(self.target.path), self.popup.toolTip())
