"""Native monitor fakes verify full-geometry association and relative DPI mapping."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from filewheel.platforms.windows import qt_position
from filewheel.ui.desktop_errors import DesktopInitializationError


def screen(name, x, y, ratio, width=1280, height=720):
    return SimpleNamespace(name=lambda: name, devicePixelRatio=lambda: ratio,
                           geometry=lambda: SimpleNamespace(x=lambda: x, y=lambda: y,
                                                           width=lambda: width, height=lambda: height))


class QtPositionTests(unittest.TestCase):
    def native(self, device=r'\\.\DISPLAY2', left=-2560, top=-200, width=2560, height=1440):
        def info(handle, pointer):
            obj = pointer._obj
            obj.device = device
            obj.monitor.left, obj.monitor.top = left, top
            obj.monitor.right, obj.monitor.bottom = left + width, top + height
            return True
        return SimpleNamespace(MonitorFromPoint=Mock(return_value=1),
                               GetMonitorInfoW=Mock(side_effect=info))

    def test_negative_monitor_origin_scaled_relative_to_origin(self):
        with (patch.object(qt_position, 'require_windows'),
              patch.object(qt_position.ctypes, 'WinDLL', return_value=self.native(), create=True)):
            self.assertEqual(qt_position.logical_point((-2060, 300),
                [screen('MAG negative', -2560, -200, 2)]), (-2310, 50))

    def test_user_friendly_name_single_monitor_capture(self):
        with (patch.object(qt_position, 'require_windows'),
              patch.object(qt_position.ctypes, 'WinDLL', return_value=self.native(
                  device=r'\\.\DISPLAY1', left=0, top=0, width=1920, height=1080), create=True)):
            self.assertEqual(qt_position.logical_point((444, 706),
                [screen('MAG 244F', 0, 0, 1, 1920, 1080)]), (444, 706))

    def test_multiple_screens_unique_full_geometry_match_not_order_or_name(self):
        with (patch.object(qt_position, 'require_windows'),
              patch.object(qt_position.ctypes, 'WinDLL', return_value=self.native(), create=True)):
            primary = screen(r'\\.\DISPLAY2', 0, 0, 1, 1920, 1080)
            matching = screen('same friendly model', -2560, -200, 2)
            for screens in ([primary, matching], [matching, primary]):
                self.assertEqual(qt_position.logical_point((-2060, 300), screens), (-2310, 50))

    def test_duplicate_mirrored_geometries_fail_even_with_one_device_name_match(self):
        with (patch.object(qt_position, 'require_windows'),
              patch.object(qt_position.ctypes, 'WinDLL', return_value=self.native(), create=True)):
            with self.assertRaises(DesktopInitializationError) as failure:
                qt_position.logical_point((-2060, 300), [
                    screen(r'\\.\DISPLAY2', -2560, -200, 2),
                    screen('Mirror', -2560, -200, 2),
                ])
            self.assertEqual(failure.exception.stage, 'match_qt_screen')
            self.assertEqual(failure.exception.details['geometry_match_count'], 2)

    def test_wrong_origin_or_dimensions_reject_despite_matching_device_name(self):
        with (patch.object(qt_position, 'require_windows'),
              patch.object(qt_position.ctypes, 'WinDLL', return_value=self.native(), create=True)):
            for candidate in (screen(r'\\.\DISPLAY2', 0, -200, 2),
                              screen(r'\\.\DISPLAY2', -2560, 0, 2),
                              screen(r'\\.\DISPLAY2', -2560, -200, 2, 1920, 1080)):
                with self.subTest(candidate=candidate), self.assertRaises(DesktopInitializationError):
                    qt_position.logical_point((-2060, 300), [candidate])

    def test_fractional_dpr_rounding_with_negative_origin(self):
        with (patch.object(qt_position, 'require_windows'),
              patch.object(qt_position.ctypes, 'WinDLL', return_value=self.native(), create=True)):
            self.assertEqual(qt_position.logical_point((-1060, 550),
                [screen('Friendly', -2560, -200, 1.5, 1707, 960)]), (-1560, 300))
            with self.assertRaises(DesktopInitializationError):
                qt_position.logical_point((-1060, 550),
                    [screen('Friendly', -2560, -200, 1.5, 1700, 960)])

    def test_invalid_peer_dpr_cannot_be_excluded_by_name(self):
        with (patch.object(qt_position, 'require_windows'),
              patch.object(qt_position.ctypes, 'WinDLL', return_value=self.native(), create=True)):
            with self.assertRaises(DesktopInitializationError) as failure:
                qt_position.logical_point((-2060, 300), [
                    screen('Good', -2560, -200, 2), screen('Other', 0, 0, float('inf')),
                ])
            self.assertEqual(failure.exception.stage, 'scale_qt_point')
            json.dumps(failure.exception.as_record(), allow_nan=False)

    def test_scaled_last_physical_pixel_stays_inside_verified_negative_screen(self):
        with (patch.object(qt_position, 'require_windows'),
              patch.object(qt_position.ctypes, 'WinDLL', return_value=self.native(), create=True)):
            # Native right/bottom are 0/1240; at2x rounding would yield -1280/520,
            # the exclusive right/bottom bounds of this Qt logical geometry.
            self.assertEqual(qt_position.logical_point((-1, 1239),
                [screen('Friendly', -2560, -200, 2)]), (-1281, 519))

    def test_unmatched_geometry_or_native_error_fails_without_guessing(self):
        native = self.native()
        with (patch.object(qt_position, 'require_windows'),
              patch.object(qt_position.ctypes, 'WinDLL', return_value=native, create=True),
              patch.object(qt_position.ctypes, 'get_last_error', return_value=87, create=True)):
            with self.assertRaises(DesktopInitializationError) as unmatched:
                qt_position.logical_point((-2000, 0), [screen('wrong', 0, 0, 1)])
            self.assertEqual(unmatched.exception.stage, "match_qt_screen")
            self.assertEqual(unmatched.exception.details["native_device"], r'\\.\DISPLAY2')
            self.assertEqual(unmatched.exception.details["qt_screen_names"], ['wrong'])
            self.assertEqual(unmatched.exception.details["physical_point"], [-2000, 0])
            json.dumps(unmatched.exception.as_record(), allow_nan=False)
            native.GetMonitorInfoW.side_effect = None
            native.GetMonitorInfoW.return_value = False
            with self.assertRaises(DesktopInitializationError) as failure:
                qt_position.logical_point((-2000, 0), [])
            self.assertEqual(failure.exception.stage, "get_monitor_info")
            self.assertEqual(failure.exception.details["winerror"], 87)
            self.assertEqual(str(failure.exception), "get_monitor_info")

    def test_monitor_lookup_failure_reports_stage_and_numeric_error(self):
        native = self.native()
        native.MonitorFromPoint.return_value = 0
        with (patch.object(qt_position, 'require_windows'),
              patch.object(qt_position.ctypes, 'WinDLL', return_value=native, create=True),
              patch.object(qt_position.ctypes, 'get_last_error', return_value=5, create=True)):
            with self.assertRaises(DesktopInitializationError) as failure:
                qt_position.logical_point((1, 2), [])
        self.assertEqual(failure.exception.as_record(), {
            "stage": "get_native_monitor", "details": {"physical_point": [1, 2], "winerror": 5},
        })
        native.GetMonitorInfoW.assert_not_called()

    def test_invalid_dpr_is_structured_without_nonfinite_json(self):
        with (patch.object(qt_position, 'require_windows'),
              patch.object(qt_position.ctypes, 'WinDLL', return_value=self.native(), create=True)):
            with self.assertRaises(DesktopInitializationError) as failure:
                qt_position.logical_point((-2000, 0), [screen(r'\\.\DISPLAY2', 0, 0, float('nan'))])
        self.assertEqual(failure.exception.stage, "scale_qt_point")
        self.assertFalse(failure.exception.details["qt_dpr_valid"])
        json.dumps(failure.exception.as_record(), allow_nan=False)

    def test_desktop_error_accepts_only_safe_bounded_metadata(self):
        for details in ({"exception": RuntimeError("private")}, {"value": float('nan')},
                        {"too_many": list(range(33))}):
            with self.assertRaises(ValueError):
                DesktopInitializationError("test_stage", details)
        error = DesktopInitializationError("test_stage", {"device": "x" * 300})
        self.assertEqual(len(error.details["device"]), 256)
        with self.assertRaises(ValueError):
            DesktopInitializationError("not a stage")
