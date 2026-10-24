"""Passive WH_MOUSE_LL source; run the message loop on its installing thread."""

from queue import Full, Queue
from time import monotonic
from typing import Callable

from filewheel.core.models import MouseEvent
from filewheel.platforms.windows.native import Native


class WindowsMouseSource:
    def __init__(self, events: Queue[MouseEvent]):
        self._native = Native()
        self._events = events
        self._hook = None
        self._callback = None  # Retained until after unhook.
        self._sequence = 0
        self.dropped_events = 0

    def run(self, stop_requested: Callable[[], bool] | None = None) -> None:
        """Block in the message pump until WM_QUIT; never suppress native input."""
        n = self._native

        def callback(code, message, data):
            try:
                if code >= 0 and message == 0x0207:  # WM_MBUTTONDOWN
                    info = n.c.cast(data, n.c.POINTER(n.MouseData)).contents
                    self._sequence += 1
                    event = MouseEvent(
                        self._sequence, (info.pt.x, info.pt.y), monotonic(),
                        n.user.GetForegroundWindow() or 0, bool(info.flags & 3),
                    )
                    try:
                        self._events.put_nowait(event)
                    except Full:
                        self.dropped_events += 1
            except Exception:
                # ctypes callbacks must not leak exceptions across the native boundary.
                self.dropped_events += 1
            return n.user.CallNextHookEx(self._hook, code, message, data)

        self._callback = n.callback_type(callback)
        self._hook = n.user.SetWindowsHookExW(
            14, self._callback, n.kernel.GetModuleHandleW(None), 0
        )
        if not self._hook:
            raise n.c.WinError(n.c.get_last_error())
        timer = None
        try:
            # Wake Python periodically so console Ctrl+C can interrupt GetMessage.
            timer = n.user.SetTimer(None, 0, 100, None)
            if not timer:
                raise n.c.WinError(n.c.get_last_error())
            message = n.w.MSG()
            while True:
                if stop_requested is not None and stop_requested():
                    break
                result = n.user.GetMessageW(n.c.byref(message), None, 0, 0)
                if result == -1:
                    raise n.c.WinError(n.c.get_last_error())
                if result == 0:
                    break
                n.user.TranslateMessage(n.c.byref(message))
                n.user.DispatchMessageW(n.c.byref(message))
        finally:
            if timer:
                n.user.KillTimer(None, timer)
            if not n.user.UnhookWindowsHookEx(self._hook):
                raise n.c.WinError(n.c.get_last_error())
            self._hook = None
            self._callback = None
