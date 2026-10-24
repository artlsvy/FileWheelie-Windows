"""Bounded Shell STA ownership; only plain JSON data crosses the thread boundary.

The collector factory, all collector calls, cleanup and COM uninitialization run
on one thread. Timeouts abandon replies rather than reusing late evidence. They
cannot interrupt a COM provider that is blocked inside a call.
"""

import json
from queue import Empty, Full, Queue
from threading import Event, Thread
from time import monotonic

from filewheel.platforms.windows.native import require_windows


def _dto_copy(value):
    """Reject proxies/opaque objects, non-string dict keys and nonfinite values."""
    def validate(item):
        if item is None or type(item) in (str, bool, int, float):
            return
        if type(item) is list:
            for child in item:
                validate(child)
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for child in item.values():
                validate(child)
            return
        raise ValueError("Shell request/result must be plain JSON data")

    validate(value)
    return json.loads(json.dumps(value, allow_nan=False))


class _WindowsStaBackend:
    """Acquire modules on the caller; initialize/pump/uninitialize on the owner."""

    def __init__(self):
        require_windows()
        import ctypes as c
        from ctypes import wintypes as w

        import comtypes

        self._comtypes = comtypes
        self._c, self._w = c, w
        self._user = c.WinDLL("user32", use_last_error=True)
        self._user.PeekMessageW.argtypes = [c.POINTER(w.MSG), w.HWND, w.UINT, w.UINT, w.UINT]
        self._user.PeekMessageW.restype = w.BOOL
        self._user.TranslateMessage.argtypes = [c.POINTER(w.MSG)]
        self._user.TranslateMessage.restype = w.BOOL
        self._user.DispatchMessageW.argtypes = [c.POINTER(w.MSG)]
        self._user.DispatchMessageW.restype = c.c_ssize_t

    def initialize(self):
        self._comtypes.CoInitializeEx(2)  # COINIT_APARTMENTTHREADED

    def pump(self):
        message = self._w.MSG()
        # Bound each pump so a message flood cannot starve pending requests.
        for _ in range(64):
            if not self._user.PeekMessageW(self._c.byref(message), None, 0, 0, 1):
                break
            self._user.TranslateMessage(self._c.byref(message))
            self._user.DispatchMessageW(self._c.byref(message))

    def uninitialize(self):
        self._comtypes.CoUninitialize()


class ShellStaWorker:
    """Own a collector with collect(hwnd, ancestry)->dict and close() on an STA.

    ``_backend`` is a private test seam for apartment lifecycle/message pumping;
    production always uses the Windows backend. Factories must not capture COM
    proxies created elsewhere. The existing application imports comtypes before
    creating this worker, so its implicit importing-thread initialization remains
    on the application thread, separate from the explicit STA reference here.
    """

    def __init__(self, factory, *, _backend=None, startup_timeout: float = 5):
        if type(startup_timeout) not in (int, float) or not 0 < startup_timeout < float("inf"):
            raise ValueError("Shell startup timeout must be finite and positive")
        self._backend = _backend if _backend is not None else _WindowsStaBackend()
        self._factory = factory
        self._requests = Queue(maxsize=1)
        self._stopped = Event()
        self._dead = Event()
        self._startup = Queue(maxsize=1)
        self._thread = Thread(target=self._run, name="explorer-shell-sta", daemon=True)
        self._thread.start()
        try:
            started = self._startup.get(timeout=startup_timeout)
        except Empty:
            self._stopped.set()
            raise TimeoutError("Shell STA startup timed out") from None
        if not started:
            self._stopped.set()
            raise RuntimeError("Shell STA startup failed")

    def collect(self, hwnd: int, ancestry: list | None, timeout: float = 0.5) -> dict:
        if self._stopped.is_set() or self._dead.is_set():
            raise RuntimeError("Shell STA is unavailable")
        if type(hwnd) is not int or hwnd <= 0 or (ancestry is not None and type(ancestry) is not list):
            raise ValueError("Invalid Shell collection request")
        if not isinstance(timeout, (int, float)) or not 0 < timeout < float("inf"):
            raise ValueError("Shell collection timeout must be finite and positive")
        try:
            request = _dto_copy({"hwnd": hwnd, "ancestry": ancestry})
        except (TypeError, ValueError, RecursionError, OverflowError):
            raise ValueError("Invalid Shell collection request") from None
        response = Queue(maxsize=1)
        expires = monotonic() + timeout
        try:
            self._requests.put_nowait((request, response, expires))
        except Full:
            raise TimeoutError("Shell STA request queue is full") from None
        try:
            success, result = response.get(timeout=max(0, expires - monotonic()))
        except Empty:
            raise TimeoutError("Shell STA collection timed out") from None
        if not success:
            raise RuntimeError("Shell STA collection failed")
        return result

    def close(self, timeout: float = 1) -> bool:
        if type(timeout) not in (int, float) or not 0 <= timeout < float("inf"):
            raise ValueError("Shell shutdown timeout must be finite and nonnegative")
        self._stopped.set()
        self._thread.join(timeout=timeout)
        return not self._thread.is_alive() and not getattr(self, "_cleanup_failed", False)

    def _run(self):
        collector = None
        initialized = False
        ready = False
        try:
            self._backend.initialize()
            initialized = True
            if self._stopped.is_set():
                return  # Startup caller already timed out; create no late COM collector.
            collector = self._factory()
            self._startup.put_nowait(True)
            ready = True
            while not self._stopped.is_set():
                self._backend.pump()
                try:
                    request, response, expires = self._requests.get(timeout=0.02)
                except Empty:
                    continue
                if self._stopped.is_set() or monotonic() >= expires:
                    continue
                result = None
                try:
                    result = collector.collect(request["hwnd"], request["ancestry"])
                    if type(result) is not dict:
                        raise ValueError("Shell collector result is not a dict")
                    result = _dto_copy(result)
                    response.put_nowait((True, result))
                except Exception:
                    # Never transport exception objects/tracebacks containing COM proxies.
                    response.put_nowait((False, None))
                finally:
                    # A rejected opaque result might itself hold COM references.
                    # Drop it here on its owner, before collector close/CoUninitialize.
                    result = None
        except Exception:
            if not ready:
                self._startup.put_nowait(False)
        finally:
            try:
                if collector is not None:
                    collector.close()
            except Exception:
                self._cleanup_failed = True
            finally:
                collector = None
                try:
                    if initialized:
                        self._backend.uninitialize()
                except Exception:
                    self._cleanup_failed = True
                self._dead.set()
