"""Physical desktop -> Qt logical coordinates; invoked after QApplication setup."""

import ctypes
import math
from ctypes import wintypes

from filewheel.platforms.windows.native import require_windows
from filewheel.ui.desktop_errors import DesktopInitializationError


def logical_point(point, screens):
    """Match the native monitor by device name, scaling relative to its origin.

    Qt keeps screen origins in native desktop layout on Windows. Dividing the
    entire desktop point by DPR would misplace monitors left of the primary.
    Failure to match is reported instead of opening on a guessed monitor.
    """
    require_windows()

    class MonitorInfo(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("monitor", wintypes.RECT),
                    ("work", wintypes.RECT), ("flags", wintypes.DWORD),
                    ("device", wintypes.WCHAR * 32)]

    user = ctypes.WinDLL("user32", use_last_error=True)
    user.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
    user.MonitorFromPoint.restype = wintypes.HANDLE
    user.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
    user.GetMonitorInfoW.restype = wintypes.BOOL
    handle = user.MonitorFromPoint(wintypes.POINT(*point), 2)
    if not handle:
        raise DesktopInitializationError("get_native_monitor", {
            "physical_point": list(point), "winerror": ctypes.get_last_error(),
        })
    info = MonitorInfo()
    info.size = ctypes.sizeof(info)
    if not user.GetMonitorInfoW(handle, ctypes.byref(info)):
        raise DesktopInitializationError("get_monitor_info", {
            "physical_point": list(point), "winerror": ctypes.get_last_error(),
        })
    screens = list(screens)
    details = {
        "physical_point": list(point), "native_device": info.device,
        "qt_screen_names": [screen.name() for screen in screens],
        "monitor_rect": [info.monitor.left, info.monitor.top,
                         info.monitor.right, info.monitor.bottom],
    }
    matches = [screen for screen in screens if screen.name().casefold() == info.device.casefold()]
    if len(matches) != 1:
        raise DesktopInitializationError("match_qt_screen", details)
    screen = matches[0]
    origin = screen.geometry()
    ratio = screen.devicePixelRatio()
    if not isinstance(ratio, (int, float)) or not math.isfinite(ratio) or ratio <= 0:
        # Keep malformed DPR out of the JSON metadata as well as coordinate math.
        raise DesktopInitializationError("scale_qt_point", {
            **details, "qt_dpr_valid": False,
        })
    return (round(origin.x() + (point[0] - info.monitor.left) / ratio),
            round(origin.y() + (point[1] - info.monitor.top) / ratio))
