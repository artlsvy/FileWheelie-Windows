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


def mapping_console_line(record: dict) -> str | None:
    """Session records use a string mapping label, events use a report object."""
    mapping = record.get("mapping")
    if not isinstance(mapping, dict):
        return None
    line = (f"{record['sequence']}: {mapping['status']} "
            f"index={mapping['candidate_index']} candidate={mapping['candidate_path']} "
            f"reason={mapping['rejection']}")
    windows = record.get("shell_candidates", {}).get("matching_windows", [])
    if len(windows) == 1:
        failure = windows[0].get("active_view_association", {})
        if "stage" in failure:
            line += f" stage={failure['stage']} hresult={failure.get('hresult_hex')}"
    return line


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enable", action="store_true", help="opt in to local filename logging")
    parser.add_argument("--dry-run-mapping", action="store_true",
                        help="report provisional index candidates; never emit trusted targets")
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
                    if args.dry_run_mapping:
                        line = mapping_console_line(record)
                        if line is not None:
                            print(line)

                resolver = ExplorerTargetResolver(write, dry_run_mapping=args.dry_run_mapping)
                controller = InvocationController(resolver)
                write({
                    "schema_version": 1, "type": "session", "windows_build": sys.getwindowsversion().build,
                    "dpi_awareness": "per_monitor_v2",
                    "python_version": sys.version.split()[0],
                    "comtypes_version": getattr(comtypes, "__version__", "unknown"),
                    "uia_apartment": "MTA",
                    "shell_apartment": "STA" if args.dry_run_mapping else "MTA",
                    "mapping": "provisional_index_dry_run" if args.dry_run_mapping else "unproven_always_none",
                })
                startup.put(None)
                ready = True
                received = 0
                while not stopped.is_set():
                    try:
                        event = events.get(timeout=0.1)
                    except Empty:
                        continue
                    received += 1
                    calls_before = resolver.counts["resolver_calls"]
                    controller.handle(event)
                    if resolver.counts["resolver_calls"] == calls_before:
                        resolver.counts["controller_skipped"] += 1
                    if failed.is_set():
                        raise RuntimeError("Diagnostic output failed")
                write({
                    "schema_version": 1, "type": "capture_summary",
                    "worker_received": received, "counts": dict(resolver.counts),
                    "queue_remaining": events.qsize(),
                    "note": "aggregate counts only; hook drops printed to console",
                })
        except Exception as error:
            failed.set()
            if not ready:
                startup.put(type(error).__name__)
            else:
                print(f"Diagnostic worker failed: {type(error).__name__}", file=sys.stderr)
        finally:
            try:
                if resolver is not None:
                    resolver.close()
                    resolver = None
            except Exception as error:
                failed.set()
                print(f"Diagnostic cleanup failed: {type(error).__name__}", file=sys.stderr)
            finally:
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
