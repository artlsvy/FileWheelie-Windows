"""Explicit local JSONL capture. Run with --enable --output logs/session.jsonl."""

import argparse
import json
import sys
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread

from filewheel.core.controller import InvocationController
from filewheel.platforms.windows.native import Native, require_windows


def write_record(stream, record: dict, failed: Event) -> None:
    """Expose write failures even when a routing controller catches exceptions."""
    try:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        stream.flush()
    except Exception:
        failed.set()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enable", action="store_true", help="opt in to local filename logging")
    parser.add_argument("--output", type=Path, required=True, help="new JSONL file; never overwritten")
    args = parser.parse_args()
    if not args.enable:
        parser.error("diagnostic logging requires --enable")
    require_windows()
    # This is a standalone process; establish physical-coordinate behavior before UIA.
    native = Native()
    if not native.user.SetProcessDpiAwarenessContext(native.c.c_void_p(-4)):
        raise native.c.WinError(native.c.get_last_error())
    # comtypes initializes its importing thread. Set its policy before that import;
    # the worker below explicitly owns its separate MTA initialization/reference.
    sys.coinit_flags = 0
    import comtypes

    from filewheel.platforms.windows.explorer_resolver import ExplorerTargetResolver
    from filewheel.platforms.windows.hook import WindowsMouseSource

    events = Queue(maxsize=64)
    startup = Queue(maxsize=1)
    stopped = Event()
    failed = Event()

    def worker() -> None:
        initialized = False
        resolver = None
        ready = False
        try:
            comtypes.CoInitializeEx(0)  # MTA, exclusively owned by this worker.
            initialized = True
            with args.output.open("x", encoding="utf-8") as stream:
                def write(record):
                    write_record(stream, record, failed)

                resolver = ExplorerTargetResolver(write)
                controller = InvocationController(resolver)
                write({
                    "schema_version": 1, "type": "session", "windows_build": sys.getwindowsversion().build,
                    "dpi_awareness": "per_monitor_v2", "mapping": "unproven_always_none",
                })
                startup.put(None)
                ready = True
                while not stopped.is_set():
                    try:
                        event = events.get(timeout=0.1)
                    except Empty:
                        continue
                    controller.handle(event)
                    if failed.is_set():
                        raise RuntimeError("Diagnostic output failed")
        except Exception as error:
            failed.set()
            if not ready:
                startup.put(type(error).__name__)
            else:
                print(f"Diagnostic worker failed: {type(error).__name__}", file=sys.stderr)
        finally:
            if resolver is not None:
                resolver.close()
                resolver = None
            if initialized:
                comtypes.CoUninitialize()

    thread = Thread(target=worker, name="explorer-evidence-mta", daemon=True)
    thread.start()
    try:
        error = startup.get(timeout=30)
        if error:
            raise RuntimeError(f"Diagnostic startup failed: {error}")
        source = WindowsMouseSource(events)
        print("Diagnostic active; local filenames may be logged. Ctrl+C stops. Mapping always returns None.")
        try:
            source.run(stop_requested=failed.is_set)
        except KeyboardInterrupt:
            pass
        print(f"Dropped hook events: {source.dropped_events}")
    finally:
        stopped.set()
        thread.join(timeout=2)
    if thread.is_alive():
        print("COM worker did not exit; evidence collection may be blocked.", file=sys.stderr)
        return 1
    return 1 if failed.is_set() else 0


if __name__ == "__main__":
    raise SystemExit(main())
