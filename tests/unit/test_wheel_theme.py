"""Readable palette roles, independently of Qt or native compositor behavior."""

import unittest

from filewheel.ui.theme import DARK, LIGHT, contrast_ratio


class WheelThemeTests(unittest.TestCase):
    def test_text_roles_meet_normal_text_contrast_in_both_appearances(self):
        for theme in (LIGHT, DARK):
            for color in (theme.text, theme.muted, theme.accent, theme.error):
                with self.subTest(theme=theme, color=color):
                    self.assertGreaterEqual(contrast_ratio(color, theme.surface), 4.5)
            self.assertGreaterEqual(contrast_ratio(theme.text, theme.hover), 4.5)
            self.assertGreaterEqual(contrast_ratio(theme.on_action, theme.action), 4.5)
            self.assertGreaterEqual(contrast_ratio(theme.outline, theme.surface), 3)
