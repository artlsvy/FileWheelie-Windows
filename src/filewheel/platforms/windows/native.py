"""Small ctypes binding loaded only on Windows; no handles opened at import time."""

import sys


def require_windows() -> None:
    if sys.platform != "win32":
        raise RuntimeError("This diagnostic requires an interactive Windows 11 desktop")


class Native:
    def __init__(self):
        require_windows()
        import ctypes as c
        from ctypes import wintypes as w

        self.c, self.w = c, w
        self.user = c.WinDLL("user32", use_last_error=True)
        self.kernel = c.WinDLL("kernel32", use_last_error=True)
        self.callback_type = c.WINFUNCTYPE(c.c_ssize_t, c.c_int, w.WPARAM, w.LPARAM)

        class MouseData(c.Structure):
            _fields_ = [
                ("pt", w.POINT), ("mouseData", w.DWORD), ("flags", w.DWORD),
                ("time", w.DWORD), ("dwExtraInfo", c.c_size_t),
            ]

        self.MouseData = MouseData
        signatures = [
            (self.user.SetWindowsHookExW, [c.c_int, self.callback_type, w.HINSTANCE, w.DWORD], w.HANDLE),
            (self.user.CallNextHookEx, [w.HANDLE, c.c_int, w.WPARAM, w.LPARAM], c.c_ssize_t),
            (self.user.UnhookWindowsHookEx, [w.HANDLE], w.BOOL),
            (self.user.GetMessageW, [c.POINTER(w.MSG), w.HWND, w.UINT, w.UINT], c.c_int),
            (self.user.TranslateMessage, [c.POINTER(w.MSG)], w.BOOL),
            (self.user.DispatchMessageW, [c.POINTER(w.MSG)], c.c_ssize_t),
            (self.user.SetTimer, [w.HWND, c.c_size_t, w.UINT, c.c_void_p], c.c_size_t),
            (self.user.KillTimer, [w.HWND, c.c_size_t], w.BOOL),
            (self.user.GetForegroundWindow, [], w.HWND),
            (self.user.WindowFromPoint, [w.POINT], w.HWND),
            (self.user.GetAncestor, [w.HWND, w.UINT], w.HWND),
            (self.user.GetClassNameW, [w.HWND, w.LPWSTR, c.c_int], c.c_int),
            (self.user.GetWindowThreadProcessId, [w.HWND, c.POINTER(w.DWORD)], w.DWORD),
            (self.user.GetDpiForWindow, [w.HWND], w.UINT),
            (self.user.SetProcessDpiAwarenessContext, [w.HANDLE], w.BOOL),
            (self.user.PostThreadMessageW, [w.DWORD, w.UINT, w.WPARAM, w.LPARAM], w.BOOL),
            (self.kernel.GetCurrentThreadId, [], w.DWORD),
            (self.kernel.GetModuleHandleW, [w.LPCWSTR], w.HMODULE),
            (self.kernel.OpenProcess, [w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
            (self.kernel.QueryFullProcessImageNameW,
             [w.HANDLE, w.DWORD, w.LPWSTR, c.POINTER(w.DWORD)], w.BOOL),
            (self.kernel.CloseHandle, [w.HANDLE], w.BOOL),
        ]
        for function, args, result in signatures:
            function.argtypes, function.restype = args, result

    def window_class(self, hwnd: int) -> str | None:
        """Read a native HWND's class, independently of UIA provider labels."""
        if (
            type(hwnd) is not int or hwnd <= 0
            or hwnd >= 1 << (self.c.sizeof(self.c.c_void_p) * 8)
        ):
            return None
        name = self.c.create_unicode_buffer(256)
        if not self.user.GetClassNameW(hwnd, name, len(name)):
            return None
        return name.value or None

    def window_evidence(self, point: tuple[int, int]) -> dict:
        c, w = self.c, self.w
        foreground = self.user.GetForegroundWindow()
        root = self.user.GetAncestor(self.user.WindowFromPoint(w.POINT(*point)), 2)
        name = c.create_unicode_buffer(256)
        self.user.GetClassNameW(root, name, len(name))
        pid = w.DWORD()
        self.user.GetWindowThreadProcessId(root, c.byref(pid))
        process = self.kernel.OpenProcess(0x1000, False, pid.value)
        image = c.create_unicode_buffer(32768)
        size = w.DWORD(len(image))
        try:
            ok = process and self.kernel.QueryFullProcessImageNameW(
                process, 0, image, c.byref(size)
            )
        finally:
            if process:
                self.kernel.CloseHandle(process)
        return {
            "foreground_hwnd": foreground or 0, "root_hwnd": root or 0,
            "class_name": name.value, "pid": pid.value,
            "process_image": image.value if ok else None,
            "dpi": self.user.GetDpiForWindow(root),
        }
