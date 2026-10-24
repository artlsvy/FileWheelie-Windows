"""Physical desktop -> Qt logical coordinates; invoked after QApplication setup."""

import ctypes
from ctypes import wintypes

from filewheel.platforms.windows.native import require_windows


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
    info = MonitorInfo()
    info.size = ctypes.sizeof(info)
    if not handle or not user.GetMonitorInfoW(handle, ctypes.byref(info)):
        raise OSError("Native monitor information unavailable")
    matches = [screen for screen in screens if screen.name().casefold() == info.device.casefold()]
    if len(matches) != 1:
        raise RuntimeError("Native monitor could not be matched to Qt screen")
    screen = matches[0]
    origin = screen.geometry()
    ratio = screen.devicePixelRatio()
    return (round(origin.x() + (point[0] - info.monitor.left) / ratio),
            round(origin.y() + (point[1] - info.monitor.top) / ratio))
