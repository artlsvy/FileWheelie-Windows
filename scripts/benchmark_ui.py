"""Repeatable QWidget/Quick CPU/event-loop benchmark (no compositor claims).

Run with the project's Python 3.14 UI environment. Synthetic preview targets
exercise existing UI code; the declared preview registry attests no converter.
"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from itertools import pairwise
from pathlib import Path
from time import monotonic, sleep


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
        end = monotonic() + 1.2
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


def worker(iterations, backend, diameter):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if backend == 'quick' and os.getenv('QT_QPA_PLATFORM') == 'offscreen':
        os.environ.setdefault('QT_QUICK_BACKEND', 'software')
    import_started = monotonic()
    from pathlib import PureWindowsPath

    from PySide6.QtCore import QEvent, QEventLoop, QPointF, Qt, QTimer, qVersion
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication

    from filewheel.converters.manager import ConversionManager
    from filewheel.converters.registry import Registry
    from filewheel.core.models import TargetResolution
    from filewheel.performance import get_recorder, summarize
    from filewheel.ui.conversion_job import ConversionJob
    from filewheel.ui.popup import RadialPopup
    if backend == 'quick':
        from filewheel.ui.quick_popup import GlassPopup
    imports_ms = (monotonic() - import_started) * 1000
    app = QApplication([])
    if backend == 'quick':
        popup = GlassPopup(point_mapper=lambda point, screens: point)
    else:
        popup = RadialPopup(point_mapper=lambda point, screens: point, diameter=diameter)
    swap_times = []
    rendered = {}
    quick_stages = {'activation': 'quick_present_to_frame', 'hover': 'quick_move_to_frame',
                    'level': 'quick_choose_to_frame'}
    if backend == 'quick':
        # Benchmark-only direct observer: timestamps/numeric counters, no GUI calls.
        # The view records each input only after its scene synchronized. Do not
        # credit an older frame that happens to swap after a new input arrives.
        def swapped():
            now = monotonic()
            swap_times.append(now)
            for stage in quick_stages.values():
                version, _ = get_recorder().latest_sample(stage)
                if version > rendered.get(stage, (0, 0))[0]:
                    rendered[stage] = (version, now)
        popup.frameSwapped.connect(swapped, Qt.ConnectionType.DirectConnection)
    graphics_api = str(popup.rendererInterface().graphicsApi()) if backend == 'quick' else 'QWidget raster'
    observed = {'activation': [], 'hover': [], 'level': []}
    target = TargetResolution(PureWindowsPath("C:/benchmark/preview.png"), 0,
                              (200, 200), monotonic(), source="shell_explicit")

    def observe(kind, operation):
        stage = quick_stages.get(kind)
        before = rendered.get(stage, (0, 0))[0]
        started = monotonic()
        operation()
        if backend == 'quick':
            deadline = monotonic() + .6
            while rendered.get(stage, (0, 0))[0] == before and monotonic() < deadline:
                app.processEvents()
                sleep(.0005)
            if rendered.get(stage, (0, 0))[0] == before:
                raise RuntimeError('Quick did not queue a rendered frame')
            observed[kind].append((rendered[stage][1] - started) * 1000)
        else:
            app.processEvents()
            app.processEvents()
            observed[kind].append((monotonic() - started) * 1000)

    observe('activation', lambda: popup.present(target))
    first_paint_at = monotonic()
    if backend == 'quick':
        graphics_api = str(popup.rendererInterface().graphicsApi())
    cold_rows = get_recorder().snapshot()
    observed = {'activation': [], 'hover': [], 'level': []}
    warm_start = len(cold_rows)
    def mouse_move(index):
        # Same reference geometry input, scaled for the QWidget size.
        scale = diameter / 240 if backend == 'widgets' else 1
        position = QPointF((115 + index % 2 * 15) * scale, (45 + index % 2 * 20) * scale)
        app.sendEvent(popup, QMouseEvent(QEvent.Type.MouseMove, position, position,
                      Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
                      Qt.KeyboardModifier.NoModifier))
    for index in range(iterations):
        observe('activation', lambda: popup.present(target))
        observe('hover', lambda index=index: mouse_move(index))
        choose = popup.session.choose if backend == 'quick' else popup._choose
        observe('level', lambda choose=choose: choose(0))
    warm_rows = get_recorder().snapshot()[warm_start:]
    animation_start = [None]
    # Keep the scene active while the real spawned fixture works.
    hover_timer = QTimer()
    hover_timer.setInterval(110)
    hover_index = [iterations - 1]  # First pulse must differ from the last warm pointer position.
    def animate_hover():
        if animation_start[0] is None:
            animation_start[0] = len(swap_times)
        hover_index[0] += 1
        mouse_move(hover_index[0])
    hover_timer.timeout.connect(animate_hover)
    hover_timer.start()

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
        hover_timer.stop()
        timeout.stop()
        if not job.wait(5000):
            raise RuntimeError("Benchmark conversion worker failed to stop")
        if not outcome or outcome[0][1] is not None:
            raise RuntimeError("Benchmark conversion fixture did not complete")
        child_isolated = job.worker_pid is not None and job.worker_pid != os.getpid()
    during_work_rows = get_recorder().snapshot()[warm_start + len(warm_rows):]
    rows = warm_rows
    animation_swaps = swap_times[animation_start[0]:] if animation_start[0] is not None else []
    intervals = [(b - a) * 1000 for a, b in pairwise(animation_swaps)]
    def stats(values):
        ordered = sorted(values)
        return ({'count': len(values), 'p50_ms': ordered[(len(ordered) - 1) // 2],
                 'p95_ms': ordered[max(0, (len(ordered) * 95 + 99) // 100 - 1)],
                 'max_ms': max(values)} if values else None)
    popup.dismiss()
    if backend == 'quick':
        popup.setSource('')
    popup.deleteLater()
    app.processEvents()
    ordered = sorted(heartbeat)
    repository = Path(__file__).resolve().parents[1]
    revision = None
    git = shutil.which('git')
    if git is not None:
        try:
            result = subprocess.run([git, '-C', str(repository), 'rev-parse', 'HEAD'],
                                    capture_output=True, text=True, check=False, timeout=5)
            revision = result.stdout.strip() if result.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            pass
    paths = ['src/filewheel/ui/popup.py', 'src/filewheel/ui/quick_popup.py',
             'src/filewheel/ui/qml/GlassWheel.qml', 'src/filewheel/ui/qml/Lens.qml']
    return {
        "qt_version": qVersion(), "machine": platform.machine(), "logical_cpus": os.cpu_count(),
        "source_revision": revision,
        "ui_source_sha256": {path: hashlib.sha256((repository / path).read_bytes()).hexdigest()
                             for path in paths},
        "backend": backend, "diameter": diameter, "platform": sys.platform,
        "graphics_api": graphics_api,
        "reduced_motion": os.getenv('FILEWHEEL_REDUCED_MOTION') == '1',
        "low_effects": os.getenv('FILEWHEEL_LOW_EFFECTS') == '1',
        "quick_backend_requested": os.getenv('QT_QUICK_BACKEND') if backend == 'quick' else None,
        "observed_operations": {key: stats(value) for key, value in observed.items()},
        "animation_frame_intervals": stats(intervals),
        "animation_frame_samples": len(animation_swaps),
        "qt_platform": app.platformName(), "python": sys.version.split()[0],
        "iterations": iterations, "imports_ms": imports_ms,
        "first_paint_at": first_paint_at, "peak_rss_bytes": peak_rss_bytes(),
        "metrics": summarize(rows), "sample_count": len(rows),
        "cold_first_activation_metrics": summarize(cold_rows),
        "during_work_metrics": summarize(during_work_rows),
        "heartbeat_spawned_conversion": {
            "samples": len(heartbeat), "interval_ms": 5,
            "p95_gap_ms": ordered[max(0, (len(ordered) * 95 + 99) // 100 - 1)]
            if ordered else None,
            "max_gap_ms": max(heartbeat) if heartbeat else None,
            "child_isolated": child_isolated,
        },
        "limits": ["Synthetic input and preview registry; no Windows hook/Explorer evidence",
                   "Widget boundary=paint dispatch; Quick boundary=frameSwapped queued for presentation",
                   "Quick preparation stages and QWidget paint CPU are not equivalent",
                   "Animation samples begin at the first 110ms hover pulse; 145ms lens motion overlaps pulses",
                   "Software offscreen frameSwapped timestamps are not native display FPS",
                   "Offscreen defaults; use QT_QPA_PLATFORM for a native desktop comparison",
                   "CPU fixture uses production ConversionJob; no real document conversion"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("widgets", "quick"), default="widgets")
    parser.add_argument("--diameter", type=int, choices=(170, 240), default=240)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 1 <= args.iterations <= 1000:
        parser.error("iterations must be between 1 and 1000")
    if sys.version_info[:2] != (3, 14):
        parser.error("run this benchmark with Python 3.14")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    if args.backend == "quick" and args.diameter != 240:
        parser.error("Quick prototype is 240px; use --diameter 240")
    if args.worker:
        print(json.dumps(worker(args.iterations, args.backend, args.diameter)))
        return
    if args.output is None:
        parser.error("--output is required")
    with tempfile.TemporaryDirectory(prefix="filewheel-timings-") as directory:
        environment = os.environ.copy()
        environment["FILEWHEEL_TIMINGS"] = str(Path(directory) / "timings.json")
        started = monotonic()
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker",
                                 "--iterations", str(args.iterations), "--backend", args.backend,
                                 "--diameter", str(args.diameter)], env=environment,
                                capture_output=True, text=True, check=True, timeout=90)
        report = json.loads(result.stdout)
        report["cold_process_to_first_paint_ms"] = (report.pop("first_paint_at") - started) * 1000
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
