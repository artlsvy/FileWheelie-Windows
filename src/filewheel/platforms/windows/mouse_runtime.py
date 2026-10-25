"""Opt-in passive Mouse3 runtime, with COM/UIA confined to its MTA worker.

No path becomes a trusted hover result. The worker may offer a copied untrusted
candidate for explicit confirmation; the unchanged Explorer resolver returns None.
"""

import sys
from queue import Empty, Queue
from threading import Event, Lock, Thread, current_thread, main_thread
from time import monotonic

from filewheel.core.controller import InvocationController
from filewheel.core.experimental import CandidateGate, candidate_from_record
from filewheel.core.models import MouseEvent
from filewheel.platforms.windows.native import require_windows

_IMPORT_LOCK = Lock()


class _WindowsMtaBackend:
    def prepare(self):
        require_windows()
        if current_thread() is not main_thread():
            raise RuntimeError("Mouse runtime must start on the application main thread")
        # comtypes owns an implicit apartment reference and an atexit cleanup.
        # Import on the main STA so its atexit CoUninitialize runs on its owner.
        # Actual UIA/Shell calls still belong exclusively to the MTA/STA workers.
        with _IMPORT_LOCK:
            if "comtypes" not in sys.modules:
                sys.coinit_flags = 2
            import comtypes
            self._comtypes = comtypes

    def initialize(self):
        require_windows()
        self._comtypes.CoInitializeEx(0)

    def uninitialize(self):
        self._comtypes.CoUninitialize()

    def create_resolver(self, write):
        import os
        from pathlib import Path
        cache = os.environ.get("FILEWHEEL_COMTYPES_CACHE")
        if cache:
            import comtypes.client
            import comtypes.gen
            Path(cache).mkdir(parents=True, exist_ok=True)
            comtypes.client.gen_dir = cache
            if cache not in comtypes.gen.__path__:
                comtypes.gen.__path__.append(cache)
        from filewheel.platforms.windows.explorer_resolver import ExplorerTargetResolver

        return ExplorerTargetResolver(write, dry_run_mapping=True)

    def create_source(self, events):
        require_windows()
        from filewheel.platforms.windows.hook import WindowsMouseSource

        return WindowsMouseSource(events)


class _ReportingResolver:
    def __init__(self, resolver, fail):
        self.resolver, self.fail = resolver, fail

    def resolve(self, event):
        try:
            return self.resolver.resolve(event)
        except Exception as error:  # noqa: BLE001 - sanitized worker/native boundary
            self.fail("mouse_evidence", error)
            return None


class MouseRuntime:
    """start()->bool; close(timeout=2)->bool. Disabled until explicitly started.

    on_candidate runs on the MTA worker and must only enqueue/emit an immutable
    DTO to the UI. on_error similarly receives a sanitized stage/type string.
    The public gate belongs to this runtime, so newer events invalidate stale UI
    confirmation tokens before any late callback can be acted upon.
    start() establishes worker/source creation; hook installation happens inside
    the unchanged source.run() and may report failure asynchronously via on_error.
    A runtime instance has one source lifetime; create a new one after shutdown.
    """

    def __init__(self, on_candidate, on_error, *, _backend=None, _clock=monotonic):
        self.gate = CandidateGate()
        self._on_candidate, self._on_error = on_candidate, on_error
        self._backend = _WindowsMtaBackend() if _backend is None else _backend
        self._clock = _clock
        self._events = Queue(maxsize=64)
        self._stop = Event()
        self._ready = Event()
        self._worker_startup = Queue(maxsize=1)
        self._hook_startup = Queue(maxsize=1)
        self._error_lock = Lock()
        self._failed = False
        self._error_callback_failed = False
        self.last_error = None
        self._cleanup_failed = False
        self._prepared = False
        self._started = False
        self._worker = None
        self._hook = None

    @property
    def threads_alive(self):
        return any(thread is not None and thread.is_alive() for thread in (self._hook, self._worker))

    @property
    def running(self):
        return self._started and self._ready.is_set() and not self._stop.is_set()

    def prepare(self):
        """Bootstrap comtypes on the main STA before asynchronous startup waits."""
        if not self._prepared:
            if hasattr(self._backend, "prepare"):
                self._backend.prepare()
            self._prepared = True

    def start(self, *, timeout: float = 5) -> bool:
        if type(timeout) not in (int, float) or not 0 < timeout < float("inf"):
            raise ValueError("Startup timeout must be finite and positive")
        if self._started:
            return self.running
        try:
            self.prepare()
        except Exception as error:  # noqa: BLE001 - startup boundary
            self._fail("mouse_com_bootstrap", error)
            return False
        self._started = True
        self._worker = Thread(target=self._run_worker, name="filewheel-mouse-mta", daemon=True)
        self._worker.start()
        expires = monotonic() + timeout
        try:
            if not self._worker_startup.get(timeout=timeout) or self._stop.is_set():
                return False
            self._hook = Thread(target=self._run_hook, name="filewheel-mouse-hook", daemon=True)
            self._hook.start()
            return (
                bool(self._hook_startup.get(timeout=max(0, expires - monotonic()))) and self.running
            )
        except Empty:
            self._fail("mouse_startup", TimeoutError())
            return False

    def close(self, *, timeout: float = 2) -> bool:
        if type(timeout) not in (int, float) or not 0 <= timeout < float("inf"):
            raise ValueError("Shutdown timeout must be finite and nonnegative")
        self._stop.set()
        self.gate.cancel()
        expires = monotonic() + timeout
        for thread in (self._hook, self._worker):
            if thread is not None and thread is not current_thread():
                thread.join(timeout=max(0, expires - monotonic()))
        return (
            all(thread is None or not thread.is_alive() for thread in (self._hook, self._worker))
            and not self._cleanup_failed
        )

    def _fail(self, stage, error):
        self._stop.set()
        self.gate.cancel()
        with self._error_lock:
            if self._failed:
                return
            self._failed = True
            self.last_error = f"{stage}: {type(error).__name__}"
        try:
            self._on_error(self.last_error)
        except Exception:  # noqa: BLE001 - callback cannot escape into COM cleanup
            self._error_callback_failed = True

    def _write(self, record):
        if self._stop.is_set():
            return
        if isinstance(record, dict) and record.get("rejection") == "evidence_error":
            self._fail("mouse_evidence", RuntimeError())
            return
        candidate = candidate_from_record(record, now=self._clock())
        self.gate.offer(candidate)
        if candidate is not None and not self._stop.is_set():
            self._on_candidate(candidate)

    def _run_worker(self):
        initialized = False
        resolver = None
        ready = False
        try:
            self._backend.initialize()
            initialized = True
            if self._stop.is_set():
                return
            resolver = self._backend.create_resolver(self._write)
            if self._stop.is_set():
                return
            controller = InvocationController(_ReportingResolver(resolver, self._fail))
            self._ready.set()
            self._worker_startup.put_nowait(True)
            ready = True
            while not self._stop.is_set():
                try:
                    event = self._events.get(timeout=0.05)
                except Empty:
                    continue
                if not isinstance(event, MouseEvent) or event.injected:
                    continue
                self.gate.cancel()
                # The return stays on the worker and is never sent to the UI.
                # Existing diagnostic resolver still returns None unconditionally.
                controller.handle(event)
        except Exception as error:  # noqa: BLE001 - sanitized worker/native boundary
            self._fail("mouse_worker", error)
        finally:
            self._ready.clear()
            if not ready:
                self._worker_startup.put_nowait(False)
            try:
                if resolver is not None:
                    resolver.close()
            except Exception as error:  # noqa: BLE001 - sanitized worker/native boundary
                self._cleanup_failed = True
                self._fail("mouse_cleanup", error)
            finally:
                resolver = None
                if initialized:
                    try:
                        self._backend.uninitialize()
                    except Exception as error:  # noqa: BLE001 - sanitized worker/native boundary
                        self._cleanup_failed = True
                        self._fail("mouse_uninitialize", error)

    def _run_hook(self):
        ready = False
        try:
            source = self._backend.create_source(self._events)
            self._hook_startup.put_nowait(True)
            ready = True
            source.run(stop_requested=self._stop.is_set)
            self._stop.set()
            self.gate.cancel()
        except Exception as error:  # noqa: BLE001 - sanitized worker/native boundary
            self._fail("mouse_hook", error)
        finally:
            if not ready:
                self._hook_startup.put_nowait(False)
