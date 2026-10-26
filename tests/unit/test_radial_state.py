import unittest
from pathlib import PureWindowsPath

from filewheel.core.models import TargetResolution
from filewheel.ui.placement import Rect, physical_to_logical, popup_position
from filewheel.ui.radial import CapabilityRegistry, PreviewCapability, RadialState


def target(name="image.png", source="shell_explicit", point=(400, 350)):
    return TargetResolution(PureWindowsPath("C:/fixtures") / name, 0, point, 1.0, source)


class RadialStateTests(unittest.TestCase):
    def test_png_declared_categories_and_formats(self):
        state = RadialState()
        self.assertTrue(state.open(target()))
        self.assertEqual(state.options, ("Image", "Document"))
        state.choose(0)
        self.assertEqual(tuple(c.output_extension for c in state.options), (".jpg", ".webp", ".tiff"))
        selection = state.choose(0)
        self.assertEqual(selection.intended_path, PureWindowsPath("C:/fixtures/image.jpg"))
        self.assertEqual(selection.original_format, "PNG")
        self.assertEqual(selection.action, "dry_run_only")
        self.assertEqual(state.stage, "confirmation")
        self.assertIsNone(state.choose(0))

    def test_docx_to_markdown_is_a_direct_destination(self):
        state = RadialState()
        state.open(target("Résumé notes.DOCX"))
        selection = state.choose(state.options.index("To MD"))
        self.assertEqual(state.stage, "confirmation")
        self.assertEqual(selection.output_extension, ".md")
        self.assertEqual(selection.intended_path.name, "Résumé notes.md")
        self.assertFalse(state.back())

    def test_markdown_from_category_keeps_back_and_format_step(self):
        state = RadialState()
        state.open(target("notes.md"))
        self.assertEqual(state.options, ("From MD",))
        self.assertIsNone(state.choose(0))
        self.assertEqual(state.stage, "formats")
        self.assertTrue(state.back())
        self.assertEqual(state.options, ("From MD",))
        state.choose(0)
        self.assertEqual(state.choose(0).output_extension, ".docx")

    def test_unknown_input_has_no_options(self):
        state = RadialState()
        state.open(target("unknown.exe"))
        self.assertEqual(state.options, ())
        self.assertIsNone(state.choose(0))

    def test_invalid_choices_do_not_transition(self):
        state = RadialState()
        state.open(target())
        for index in (-1, 99, True, 1.0, None, "0"):
            self.assertIsNone(state.choose(index))
            self.assertEqual(state.stage, "categories")

    def test_reopening_resets_and_none_closes(self):
        state = RadialState()
        state.open(target())
        state.choose(0)
        state.choose(0)
        state.open(target("new.docx", "explorer_hover"))
        self.assertEqual(state.stage, "categories")
        self.assertIsNone(state.selection)
        self.assertIsNone(state.category)
        self.assertFalse(state.open(None))
        self.assertEqual(state.stage, "closed")
        self.assertIsNone(state.target)

    def test_registry_injection_controls_choices(self):
        registry = CapabilityRegistry((PreviewCapability(".png", "Image", ".bmp", "BMP"),))
        state = RadialState(registry)
        state.open(target())
        self.assertEqual(state.options, ("Image",))
        state.choose(0)
        self.assertEqual(state.choose(0).output_extension, ".bmp")

    def test_registry_rejects_bad_or_duplicate_edges(self):
        for args in (("png", "Image", ".jpg", "JPEG"),
                     (".png", "Bogus", ".jpg", "JPEG"),
                     (".png", "Image", ".png", "PNG"),
                     (".png", "Image", ".jpg", "")):
            with self.assertRaises(ValueError):
                PreviewCapability(*args)
        edge = PreviewCapability(".png", "Image", ".jpg", "JPEG")
        with self.assertRaises(ValueError):
            CapabilityRegistry((edge, edge))


class RadialPlacementTests(unittest.TestCase):
    def test_center_and_workarea_edges(self):
        area = Rect(0, 0, 1920, 1040)
        self.assertEqual(popup_position((600, 500), area), (438, 338))
        self.assertEqual(popup_position((0, 0), area), (6, 6))
        self.assertEqual(popup_position((1920, 1080), area), (1590, 710))

    def test_negative_monitor_and_mixed_dpi_origin(self):
        physical = Rect(-2560, 0, 2560, 1440)
        logical = Rect(-2560, 0, 1706.6666667, 960)
        point = physical_to_logical((-1280, 720), physical, logical)
        self.assertAlmostEqual(point[0], -1706.66666665)
        self.assertEqual(point[1], 480)
        self.assertEqual(popup_position((-2550, 5), Rect(-2560, 0, 1707, 920)), (-2554, 6))

    def test_tiny_monitor_anchors_and_bad_geometry_rejects(self):
        self.assertEqual(popup_position((0, 0), Rect(-40, -20, 100, 100)), (-40, -20))
        with self.assertRaises(ValueError):
            popup_position((float("nan"), 0), Rect(0, 0, 800, 600))
        with self.assertRaises(ValueError):
            physical_to_logical((0, 0), Rect(0, 0, 0, 1), Rect(0, 0, 1, 1))
