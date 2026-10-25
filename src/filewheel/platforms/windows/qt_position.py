"""Physical desktop -> Qt logical coordinates; invoked after QApplication setup."""

import ctypes
import math
from ctypes import wintypes

from filewheel.platforms.windows.native import require_windows
from filewheel.ui.desktop_errors import DesktopInitializationError


def logical_point(point, screens):
    """Match one native/Qt full monitor geometry, scaling relative to its origin.

    Qt keeps screen origins in native desktop layout on Windows. Dividing the
    entire desktop point by DPR would misplace monitors left of the primary.
    Qt screen names can be friendly model names rather than Win32 device names.
    Require unique origin and DPR-scaled dimensions instead; duplicate/mirrored
    or contradictory geometries fail closed rather than choosing by name/order.
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
    candidates = []
    qt_screens = []
    invalid_dpr = False
    for screen in screens:
        origin = screen.geometry()
        ratio = screen.devicePixelRatio()
        valid_ratio = type(ratio) in (int, float) and math.isfinite(ratio) and ratio > 0
        geometry = [origin.x(), origin.y(), origin.width(), origin.height()]
        qt_screens.append({
            "name": screen.name(), "geometry": geometry,
            "dpr": ratio if valid_ratio else None,
        })
        if not valid_ratio:
            invalid_dpr = True
            continue
        # At most one logical pixel of size rounding can be introduced by Qt.
        tolerance = max(1.0, ratio)
        if (geometry[0] == info.monitor.left and geometry[1] == info.monitor.top
                and geometry[2] > 0 and geometry[3] > 0
                and abs(geometry[2] * ratio - (info.monitor.right - info.monitor.left)) <= tolerance
                and abs(geometry[3] * ratio - (info.monitor.bottom - info.monitor.top)) <= tolerance):
            candidates.append((screen, origin, ratio))
    details["qt_screens"] = qt_screens
    if invalid_dpr:
        # An unmeasurable screen cannot be excluded from a uniqueness proof.
        raise DesktopInitializationError("scale_qt_point", {
            **details, "qt_dpr_valid": False,
        })
    if len(candidates) != 1:
        raise DesktopInitializationError("match_qt_screen", {
            **details, "geometry_match_count": len(candidates),
        })
    screen, origin, ratio = candidates[0]
    x = round(origin.x() + (point[0] - info.monitor.left) / ratio)
    y = round(origin.y() + (point[1] - info.monitor.top) / ratio)
    # At a scaled monitor edge, rounding may reach the exclusive screen bound.
    # Clamp within the already uniquely verified screen; never choose a peer.
    return (min(max(x, origin.x()), origin.x() + origin.width() - 1),
            min(max(y, origin.y()), origin.y() + origin.height() - 1))
