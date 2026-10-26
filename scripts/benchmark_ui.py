"""Repeatable local QWidget CPU/event-loop benchmark (no compositor claims).

Run with the project's Python 3.14 UI environment. Synthetic preview targets
exercise existing UI code; the declared preview registry attests no converter.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from time import monotonic


class BusyEngine:
    """Deterministic local CPU fixture using the production process supervisor."""

    engine_id = "benchmark-busy"

    @property
    def capabilities(self):
        from filewheel.converters.base import Capability
        return (Capability(".sample", "Document", ".json", "JSON", self.engine_id),)

    def available(self):
        return True

    def convert(self, source, extension, workdir, progress, cancel):
        from filewheel.converters.base import EngineOutput, check_cancel
        end = monotonic() + .4
        while monotonic() < end:
            check_cancel(cancel)
        output = workdir / "result.json"
        output.write_text('{"fixture":true}', encoding="utf-8")
        progress(1., "Finished")
        return (EngineOutput(output, "result.json"),)

    def validate(self, output):
        if json.loads(output.path.read_text(encoding="utf-8")) != {"fixture": True}:
            raise ValueError("Invalid benchmark fixture output")


def peak_rss_bytes():
    try:
        import resource
        amount = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(amount if sys.platform == "darwin" else amount * 1024)
    except ImportError:
        return None


def worker(iterations):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import_started = monotonic()
    from pathlib import PureWindowsPath

    from PySide6.QtCore import QEvent, QEventLoop, QPointF, Qt, QTimer
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication

    from filewheel.converters.manager import ConversionManager
    from filewheel.converters.registry import Registry
    from filewheel.core.models import TargetResolution
    from filewheel.performance import get_recorder, summarize
    from filewheel.ui.conversion_job import ConversionJob
    from filewheel.ui.popup import RadialPopup
    imports_ms = (monotonic() - import_started) * 1000
    app = QApplication([])
    popup = RadialPopup(point_mapper=lambda point, screens: point)
    target = TargetResolution(PureWindowsPath("C:/benchmark/preview.png"), 0,
                              (200, 200), monotonic(), source="shell_explicit")

    def paint_events():
        # Two bounded dispatches handle show/update and posted paint delivery.
        app.processEvents()
        app.processEvents()

    popup.present(target)
    paint_events()
    first_paint_at = monotonic()
    cold_rows = get_recorder().snapshot()
    warm_start = len(cold_rows)
    for index in range(iterations):
        popup.present(target)
        paint_events()
        angle = index % 2
        position = QPointF(115 + angle * 15, 45 + angle * 20)
        app.sendEvent(popup, QMouseEvent(QEvent.Type.MouseMove, position, position,
                      Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
                      Qt.KeyboardModifier.NoModifier))
        paint_events()
        popup._choose(0)
        paint_events()
    popup.dismiss()
    paint_events()

    heartbeat = []
    timer = QTimer()
    timer.setInterval(5)
    previous = [monotonic()]

    def tick():
        now = monotonic()
        heartbeat.append((now - previous[0]) * 1000)
        previous[0] = now

    timer.timeout.connect(tick)
    with tempfile.TemporaryDirectory(prefix="filewheel-benchmark-") as directory:
        source = Path(directory) / "input.sample"
        source.write_text("fixture", encoding="utf-8")
        manager = ConversionManager(Registry((BusyEngine(),)))
        job = ConversionJob(manager, source, ".json")
        loop = QEventLoop()
        outcome = []
        job.outcome.connect(lambda result, error: (outcome.append((result, error)), loop.quit()))
        timeout = QTimer()
        timeout.setSingleShot(True)
        timeout.timeout.connect(lambda: (job.cancelled.set(), loop.quit()))
        timer.start()
        timeout.start(15000)
        job.start()
        loop.exec()
        timer.stop()
        timeout.stop()
        if not job.wait(5000):
            raise RuntimeError("Benchmark conversion worker failed to stop")
        if not outcome or outcome[0][1] is not None:
            raise RuntimeError("Benchmark conversion fixture did not complete")
        child_isolated = job.worker_pid is not None and job.worker_pid != os.getpid()
    recorder = get_recorder()
    rows = recorder.snapshot()[warm_start:]
    ordered = sorted(heartbeat)
    return {
        "backend": "widgets", "platform": sys.platform,
        "qt_platform": app.platformName(), "python": sys.version.split()[0],
        "iterations": iterations, "imports_ms": imports_ms,
        "first_paint_at": first_paint_at, "peak_rss_bytes": peak_rss_bytes(),
        "metrics": summarize(rows), "sample_count": len(rows),
        "cold_first_activation_metrics": summarize(cold_rows),
        "heartbeat_spawned_conversion": {
            "samples": len(heartbeat), "interval_ms": 5,
            "p95_gap_ms": ordered[max(0, (len(ordered) * 95 + 99) // 100 - 1)]
            if ordered else None,
            "max_gap_ms": max(heartbeat) if heartbeat else None,
            "child_isolated": child_isolated,
        },
        "limits": ["Synthetic input and preview registry; no Windows hook/Explorer evidence",
                   "Paint callback completion measures CPU/event dispatch, not displayed frames",
                   "Offscreen defaults; use QT_QPA_PLATFORM for a native desktop comparison",
                   "CPU fixture uses production ConversionJob; no real document conversion"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("widgets",), default="widgets")
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 1 <= args.iterations <= 1000:
        parser.error("iterations must be between 1 and 1000")
    if sys.version_info[:2] != (3, 14):
        parser.error("run this benchmark with Python 3.14")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    if args.worker:
        print(json.dumps(worker(args.iterations)))
        return
    if args.output is None:
        parser.error("--output is required")
    with tempfile.TemporaryDirectory(prefix="filewheel-timings-") as directory:
        environment = os.environ.copy()
        environment["FILEWHEEL_TIMINGS"] = str(Path(directory) / "timings.json")
        started = monotonic()
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker",
                                 "--iterations", str(args.iterations)], env=environment,
                                capture_output=True, text=True, check=True, timeout=90)
        report = json.loads(result.stdout)
        report["cold_process_to_first_paint_ms"] = (report.pop("first_paint_at") - started) * 1000
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
