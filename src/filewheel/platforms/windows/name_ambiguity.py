"""Bounded, conservative filename-collision evidence for provisional Shell items.

Only exact full filename labels qualify. The two literal-name searches below
do not walk the directory in Python: at most one exact result and two
wildcard results are consumed. Filesystem/provider internals can still affect latency. Win32 also matches short aliases, so every different
returned long name rejects rather than attempting to interpret Shell policy.
This is supplementary ambiguity evidence, never trusted hover identity.

API contract (including short-name matches and terminal error codes):
https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-findfirstfilew
https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-findnextfilew
"""

from filewheel.core.index_mapping import _local_file_path
from filewheel.platforms.windows.native import require_windows


class _WindowsSearch:
    def __init__(self):
        require_windows()
        import ctypes as c
        from ctypes import wintypes as w

        class FindData(c.Structure):
            _fields_ = [
                ("attributes", w.DWORD), ("created", w.FILETIME),
                ("accessed", w.FILETIME), ("written", w.FILETIME),
                ("size_high", w.DWORD), ("size_low", w.DWORD),
                ("reserved0", w.DWORD), ("reserved1", w.DWORD),
                ("name", w.WCHAR * 260), ("alternate", w.WCHAR * 14),
            ]

        self.c, self.data_type = c, FindData
        self.kernel = c.WinDLL("kernel32", use_last_error=True)
        self.kernel.FindFirstFileW.argtypes = [w.LPCWSTR, c.POINTER(FindData)]
        self.kernel.FindFirstFileW.restype = w.HANDLE
        self.kernel.FindNextFileW.argtypes = [w.HANDLE, c.POINTER(FindData)]
        self.kernel.FindNextFileW.restype = w.BOOL
        self.kernel.FindClose.argtypes = [w.HANDLE]
        self.kernel.FindClose.restype = w.BOOL
        self.invalid_handle = c.c_void_p(-1).value

    def first(self, pattern):
        data = self.data_type()
        handle = self.kernel.FindFirstFileW(pattern, self.c.byref(data))
        if handle == self.invalid_handle:
            raise self.c.WinError(self.c.get_last_error())
        return handle, data.name

    def next(self, handle):
        data = self.data_type()
        if not self.kernel.FindNextFileW(handle, self.c.byref(data)):
            error = self.c.get_last_error()
            if error == 18:  # ERROR_NO_MORE_FILES, not an arbitrary query failure.
                return None
            raise self.c.WinError(error)
        return data.name

    def close(self, handle):
        if not self.kernel.FindClose(handle):
            raise self.c.WinError(self.c.get_last_error())


def probe_name_ambiguity(path: str, name: str, *, backend=None) -> dict:
    """Return unique/ambiguous/unproven without accepting shortened labels.

    Each search handle is closed, including on early rejection or query failure.
    A wildcard result cap is rejection, never a partial listing called complete.
    """
    result = {
        "method": "literal_name_collision_probe", "status": "unproven",
        "candidate_path": path, "name": name, "query_count": 0,
    }
    target = _local_file_path(path)
    if (target is None or not isinstance(name, str) or name != target.name
            or len(name) > 255):
        return result
    try:
        search = _WindowsSearch() if backend is None else backend
        result["query_count"] += 1
        handle, exact_name = search.first(str(target))
        try:
            if exact_name != name:
                result["status"] = "ambiguous"
                return result
        finally:
            search.close(handle)
        result["query_count"] += 1
        try:
            handle, found = search.first(str(target.parent / (name + ".*")))
        except OSError as error:
            if getattr(error, "winerror", None) == 2:  # ERROR_FILE_NOT_FOUND only.
                result["status"] = "unique"
                return result
            raise
        try:
            if found != name:
                result["status"] = "ambiguous"
                return result
            result["query_count"] += 1
            found = search.next(handle)
            # Even a repeated result is unsafe: the bounded search did not end.
            result["status"] = "unique" if found is None else "ambiguous"
            return result
        finally:
            search.close(handle)
    except (OSError, RuntimeError):
        result["status"] = "unproven"
        return result
