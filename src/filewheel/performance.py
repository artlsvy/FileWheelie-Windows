"""Opt-in, bounded local timing probes; no Qt imports or per-event disk writes.

Set FILEWHEEL_TIMINGS to an explicit absolute JSON output path before startup.
Paint completion is a Qt CPU boundary, not evidence of compositor presentation.
"""

import atexit
import json
import math
import os
from collections import deque
from pathlib import Path
from threading import Lock
from time import monotonic

STAGES = frozenset({
    "mouse_queue_age", "resolver", "candidate_from_event", "present_to_show",
    "present_to_paint", "show_to_paint", "move_to_paint", "choose_to_paint",
    "paint_wall", "paint_cpu", "candidate_to_ui", "candidate_to_show",
    "registry_startup", "quick_present_to_sync", "quick_move_to_sync", "quick_choose_to_sync",
})


def summarize(records):
    """Nearest-rank percentiles, milliseconds, grouped by fixed stage name."""
    result = {}
    for stage in sorted(STAGES):
        values = sorted(row["duration_ms"] for row in records if row["stage"] == stage)
        if values:
            result[stage] = {
                "count": len(values),
                "p50_ms": values[math.ceil(len(values) * .5) - 1],
                "p95_ms": values[math.ceil(len(values) * .95) - 1],
                "max_ms": values[-1],
            }
    return result


class TimingRecorder:
    def __init__(self, output=None, *, capacity=10000):
        self.output = None
        try:
            path = Path(output) if output else None
            if path is not None and path.is_absolute() and path.suffix.lower() == ".json":
                self.output = path
        except (ValueError, TypeError, OSError):
            pass
        self.enabled = self.output is not None
        self._records = deque(maxlen=max(1, capacity))
        self._lock = Lock()
        self._flushed = False

    def record(self, stage, duration_ms):
        if not self.enabled:
            return
        if (type(stage) is not str or stage not in STAGES or type(duration_ms) not in (int, float)
                or not math.isfinite(duration_ms) or duration_ms < 0):
            return
        with self._lock:
            self._records.append({"stage": stage, "duration_ms": duration_ms})

    def snapshot(self):
        with self._lock:
            return [dict(row) for row in self._records]

    def flush(self):
        if not self.enabled:
            return False
        try:
            # Refuse existing files (including links); never clobber a user file
            # through an opt-in environment variable. Flush is intentionally once.
            with self._lock:
                if self._flushed:
                    return False
                rows = [dict(row) for row in self._records]
                with self.output.open("x", encoding="utf-8") as stream:
                    json.dump({"records": rows, "metrics": summarize(rows)}, stream, indent=2)
                self._flushed = True
            return True
        except (OSError, ValueError, TypeError):
            # Diagnostics must never break invocation or application shutdown.
            return False


_recorder = TimingRecorder(os.environ.get("FILEWHEEL_TIMINGS"))
atexit.register(_recorder.flush)


def get_recorder():
    return _recorder


def record(stage, duration_ms):
    _recorder.record(stage, duration_ms)


def elapsed_ms(start):
    return (monotonic() - start) * 1000
