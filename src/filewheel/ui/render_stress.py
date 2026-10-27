"""Windows-only real Quick UI cycles with a controlled worker, no real files."""
import json
import os
import platform
import sys
from pathlib import Path, PureWindowsPath
from threading import Event
from time import monotonic, process_time


def run(output, cycles=100):
    if sys.platform != 'win32' or os.getenv('QT_QPA_PLATFORM', 'windows') != 'windows':
        raise RuntimeError('Stress test requires the interactive Windows platform')
    from PySide6.QtCore import QEventLoop, QPoint, Qt, QTimer, qVersion
    from PySide6.QtGui import QCursor
    from PySide6.QtWidgets import QApplication, QWidget

    from filewheel.converters.base import ConversionCancelled, ConversionResult
    from filewheel.core.models import TargetResolution
    from filewheel.ui.quick_popup import GlassPopup
    from filewheel.ui.radial import DEFAULT_PREVIEW_REGISTRY

    class Worker:
        def __init__(self):
            self.release = Event()

        def convert(self, source, extension, *, progress, cancel):
            progress(.3, 'Controlled UI work')
            while not self.release.wait(.01):
                if cancel.is_set():
                    raise ConversionCancelled('Controlled cancellation')
            return ConversionResult((Path('C:/preview/output.png'),), (), 'preview')

    def wait(ms):
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def pump(predicate, label='worker completion'):
        deadline = monotonic() + 5
        while not predicate() and monotonic() < deadline:
            wait(10)
        assert predicate(), 'UI state deadline exceeded: ' + label

    import ctypes
    from ctypes import wintypes

    class Memory(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD)] + [
            (key, ctypes.c_size_t) for key in ('peak_ws', 'ws', 'peak_pool', 'pool',
                                               'peak_nonpool', 'nonpool', 'page', 'peak_page')]

    def resources():
        info = Memory()
        info.cb = ctypes.sizeof(info)
        handle = ctypes.c_void_p(-1)
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(info), info.cb)
        return {'working_set': info.ws if ok else None,
                    'gdi': ctypes.windll.user32.GetGuiResources(handle, 0),
                    'user': ctypes.windll.user32.GetGuiResources(handle, 1)}

    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication(['Filewheel UI stress'])
    app.setQuitOnLastWindowClosed(False)
    worker = Worker()
    view = GlassPopup(DEFAULT_PREVIEW_REGISTRY, manager=worker, point_mapper=lambda p, s: p)
    backdrop = QWidget()
    backdrop.setStyleSheet('background: #804080;')
    area = app.primaryScreen().availableGeometry()
    backdrop.setGeometry(area)
    backdrop.show()
    # Let the backing window's initial activation settle BEFORE opening a Popup.
    # Otherwise its delayed activation can legitimately dismiss selection.
    pump(lambda: backdrop.windowHandle() is not None and backdrop.windowHandle().isExposed(),
         'backdrop exposure')
    wait(150)
    target = TargetResolution(PureWindowsPath('C:/preview/input.png'), 0,
                              (area.center().x(), area.center().y()), monotonic(), 'shell_explicit')
    rows = []
    counters = {'frames': 0, 'initialized': 0, 'invalidated': 0}

    def increment(key):
        counters[key] += 1

    def attach(surface):
        surface.frameSwapped.connect(lambda: increment('frames'), Qt.ConnectionType.QueuedConnection)
        surface.sceneGraphInitialized.connect(lambda: increment('initialized'), Qt.ConnectionType.QueuedConnection)
        surface.sceneGraphInvalidated.connect(lambda: increment('invalidated'), Qt.ConnectionType.QueuedConnection)

    attach(view)
    attached = None
    started, cpu = monotonic(), process_time()
    report = {'pid': os.getpid(), 'qt': qVersion(), 'windows': platform.version(),
                  'quick': os.getenv('QT_QUICK_BACKEND'), 'rhi': os.getenv('QSG_RHI_BACKEND'),
                  'cycles': rows, 'passed': False}

    def capture(surface, label, index):
        # Capture compositor pixels BEFORE grabWindow can force another render.
        point = surface.mapToGlobal(QPoint(0, 0))
        screen = surface.screen()
        origin = screen.geometry().topLeft()
        desktop = screen.grabWindow(0, point.x()-origin.x(), point.y()-origin.y(),
                                    surface.width(), surface.height()).toImage()
        assert not desktop.isNull(), 'Desktop capture unavailable (locked/session?)'
        # Known solid backdrop: require actual pill material in a broad interior.
        scaled = desktop.scaled(surface.width(), surface.height())
        samples = [scaled.pixelColor(x, y) for x in range(30, 240, 10) for y in (30, 40)]
        present = sum(abs(c.red()-128)+abs(c.green()-64)+abs(c.blue()-128) > 45
                      for c in samples) > 30
        if not present:
            desktop.save(str(output / f'failure-{index}-{label}-desktop.png'))
            surface.grabWindow().save(str(output / f'failure-{index}-{label}-render.png'))
            surface.render_diagnostics.snapshot('capture_failure')
        assert present, f'Progress not present in desktop pixels: cycle {index} {label}'
        rendered = surface.grabWindow()
        assert not rendered.isNull(), 'No render target pixels'
        assert rendered.pixelColor(rendered.width()//2, rendered.height()//2).alpha() > 0
        if index in (1, cycles):
            desktop.save(str(output / f'{index}-{label}-desktop.png'))
            rendered.save(str(output / f'{index}-{label}-render.png'))
        return bytes(desktop.constBits())

    try:
        for index in range(1, cycles+1):
            cycle_start = monotonic()
            worker.release.clear()
            # Popup focus dismissal is expected behavior, not a lost progress
            # surface. Record bounded selection reopens, never retry a job/pill.
            selection_reopens = 0
            for attempt in range(3):
                assert view.present(target)
                QCursor.setPos(view.mapToGlobal(QPoint(120, 120)))
                wait(180)
                if view.isExposed() and view.state.stage == 'categories':
                    break
                selection_reopens += 1
            else:
                raise AssertionError('Selection remained dismissed/unexposed after three opens')
            view.session.choose(0)
            view.session.choose(0)
            assert view.job is not None
            view.collapse_progress()
            surface = view.progress_view
            assert surface is not None
            if attached is not surface:
                attach(surface)
                attached = surface
            # Alternate completion within morph and live animation checks.
            early = index % 4 == 0
            if early:
                worker.release.set()
            wait(300)
            assert not view._transitioning
            before = counters['frames']
            first = capture(surface, 'compact', index)
            wait(350)
            second = capture(surface, 'animated', index)
            if not early:
                assert counters['frames'] > before, 'No submitted animation frames'
                assert first != second, 'Desktop animation pixels unchanged'
            view.expand_progress()
            wait(70)
            capture(surface, 'expanded', index)
            backdrop.activateWindow()
            wait(40)
            view.collapse_progress()
            view.expand_progress()
            view.collapse_progress()
            cancelled = index % 5 == 0 and not early
            if cancelled:
                view.session.request_cancel()
            else:
                worker.release.set()
            pump(lambda: view.job is None)
            wait(250)
            assert view.session.presentation == ('cancelled' if cancelled else 'succeeded')
            capture(surface, 'result', index)
            # Exercise actual expiry callback/fade with shortened success dwell.
            if cancelled:
                view.dismiss_progress()
            else:
                view.success_timer.stop()
                view._expire_success()
                wait(220)
            assert not surface.isVisible() and view.job is None
            row = dict(index=index, api=view.render_diagnostics.api,
                       progress_api=surface.render_diagnostics.api,
                       selection_reopens=selection_reopens,
                       elapsed_ms=round((monotonic()-cycle_start)*1000),
                       **counters, **resources())
            rows.append(row)
            output.joinpath('result.json').write_text(json.dumps(report, indent=2))
        report['passed'] = True
    except Exception as error:  # noqa: BLE001 - save failed native test evidence before cleanup
        report['error'] = type(error).__name__ + ': ' + str(error)
        report['failure_state'] = {'stage': view.state.stage, 'visible': view.isVisible(),
            'exposed': view.isExposed(), 'active': view.isActive(), 'job': view.job is not None,
            'presentation': view.session.presentation}
    finally:
        report.update(elapsed_s=monotonic()-started, cpu_s=process_time()-cpu)
        output.joinpath('result.json').write_text(json.dumps(report, indent=2))
        worker.release.set()
        pump(lambda: view.job is None)
        view.shutdown()
        backdrop.close()
        view.deleteLater()
        app.processEvents()
    return 0 if report['passed'] else 1
