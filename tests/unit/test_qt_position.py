"""Native monitor API fakes verify device matching and relative DPI mapping."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from filewheel.platforms.windows import qt_position
from filewheel.ui.desktop_errors import DesktopInitializationError


def screen(name, x, y, ratio):
    return SimpleNamespace(name=lambda: name, devicePixelRatio=lambda: ratio,
                           geometry=lambda: SimpleNamespace(x=lambda: x, y=lambda: y))


class QtPositionTests(unittest.TestCase):
    def native(self, device=r'\\.\DISPLAY2', left=-2560, top=-200):
        def info(handle, pointer):
            obj = pointer._obj
            obj.device = device
            obj.monitor.left, obj.monitor.top = left, top
            return True
        return SimpleNamespace(MonitorFromPoint=Mock(return_value=1),
                               GetMonitorInfoW=Mock(side_effect=info))

    def test_negative_monitor_origin_scaled_relative_to_origin(self):
        with (patch.object(qt_position, 'require_windows'),
              patch.object(qt_position.ctypes, 'WinDLL', return_value=self.native(), create=True)):
            self.assertEqual(qt_position.logical_point((-2060, 300),
                [screen(r'\\.\DISPLAY2', -2560, -200, 2)]), (-2310, 50))

    def test_unmatched_device_or_native_error_fails_without_guessing(self):
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
