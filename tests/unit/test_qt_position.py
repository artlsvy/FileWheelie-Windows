"""Native monitor API fakes verify device matching and relative DPI mapping."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from filewheel.platforms.windows import qt_position


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
              patch.object(qt_position.ctypes, 'WinDLL', return_value=native, create=True)):
            with self.assertRaises(RuntimeError):
                qt_position.logical_point((-2000, 0), [screen('wrong', 0, 0, 1)])
            native.GetMonitorInfoW.side_effect = None
            native.GetMonitorInfoW.return_value = False
            with self.assertRaises(OSError):
                qt_position.logical_point((-2000, 0), [])
