"""Keep Setup/Uninstall from replacing a running desktop or conversion host."""
import ctypes
from ctypes import wintypes


def retain_until_exit():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
    kernel.CreateMutexW.restype = wintypes.HANDLE
    handle = kernel.CreateMutexW(None, False, r'Local\Filewheel.Desktop')
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    # Intentionally retained until OS process teardown, including child cleanup.
    return handle
