"""Cancellation deadlines with real spawned, deliberately uncooperative engines."""
import json
import os
import tempfile
import time
from pathlib import Path
from threading import Event
from unittest.mock import Mock, patch

import pytest

from filewheel.converters import (
    Capability,
    ConversionCancelled,
    ConversionError,
    ConversionManager,
    EngineOutput,
    Registry,
)
from filewheel.converters.process_worker import run_in_process


class StuckEngine:
    engine_id = 'stuck-fixture'
    capabilities = (Capability('.sample', 'Document', '.json', 'JSON', engine_id),)

    def __init__(self, stage='convert'):
        self.stage = stage

    def available(self):
        return True

    def convert(self, source, extension, workdir, progress, cancel):
        output = workdir / 'output.json'
        output.write_text('{}')
        time.sleep(.07)
        progress(.1, 'Entered native conversion')
        if self.stage == 'convert':
            time.sleep(10)  # Simulate a native call which ignores cancellation.
        time.sleep(.07)  # Make the next progress sample visible through throttling.
        return (EngineOutput(output, 'output.json'),)

    def validate(self, output):
        if self.stage == 'validate':
            time.sleep(10)
        json.loads(output.path.read_text())


class SlowPublicationManager(ConversionManager):
    def convert(self, source, extension, **kwargs):
        permission, progress = kwargs['before_publish'], kwargs['progress']
        def before_publish():
            permission()
            time.sleep(.07)
            progress(.95, 'Publication permitted')
            time.sleep(.4)
        kwargs['before_publish'] = before_publish
        return super().convert(source, extension, **kwargs)


@pytest.mark.parametrize('stage', ['convert', 'validate'])
def test_stuck_conversion_cancel_is_bounded_cleans_stage_and_allows_same_file_retry(tmp_path, stage):
    source = tmp_path / 'Unicode æ source.sample'
    source.write_bytes(b'original')
    existing = tmp_path / 'output.json'
    existing.write_text('existing output')
    cancel = Event()
    pids = []
    manager = ConversionManager(Registry((StuckEngine(stage),)))
    started = time.monotonic()
    with pytest.raises(ConversionCancelled) as caught:
        run_in_process(manager, source, '.json', cancel=cancel,
                       progress=lambda *args: cancel.set(), on_started=pids.append, _cancel_grace=.2)
    assert time.monotonic() - started < 5
    assert caught.value.engine_id == StuckEngine.engine_id
    assert caught.value.kind == 'conversion_cancelled'
    assert not list(tmp_path.glob('.filewheel-*'))
    assert existing.read_text() == 'existing output'
    assert source.read_bytes() == b'original'
    assert len(pids) == 1
    # Real process handle has been reaped before the caller can retry.
    if os.name != 'nt':
        with pytest.raises(ProcessLookupError):
            os.kill(pids[0], 0)
    cancel.clear()
    result = run_in_process(ConversionManager(Registry((StuckEngine('none'),))), source, '.json',
                            cancel=cancel, progress=lambda *args: None)
    assert result.path.name == 'output (2).json'
    assert json.loads(result.path.read_text()) == {}
    assert existing.read_text() == 'existing output'


def test_cancel_at_publication_gate_does_not_publish(tmp_path):
    source = tmp_path / 'source.sample'
    source.write_bytes(b'original')
    cancel = Event()
    with pytest.raises(ConversionCancelled):
        run_in_process(ConversionManager(Registry((StuckEngine('none'),))), source, '.json',
                       cancel=cancel, progress=lambda fraction, _: cancel.set() if fraction == .9 else None,
                       _cancel_grace=.1)
    assert not (tmp_path / 'output.json').exists()
    assert not list(tmp_path.glob('.filewheel-*'))


def test_cancel_after_publication_permission_waits_for_transaction_without_killing(tmp_path):
    source = tmp_path / 'source.sample'
    source.write_bytes(b'original')
    cancel = Event()
    with patch('filewheel.converters.process_worker._stop_owned_worker',
               side_effect=AssertionError('Must not terminate a publisher')), \
            pytest.raises(ConversionCancelled):
        run_in_process(SlowPublicationManager(Registry((StuckEngine('none'),))), source, '.json',
                           cancel=cancel,
                           progress=lambda fraction, _: cancel.set() if fraction == .95 else None,
                           _cancel_grace=.05)
    assert not (tmp_path / 'output.json').exists()
    assert not list(tmp_path.glob('.filewheel-*'))


def test_windows_stop_targets_only_owned_pid_tree_and_joins():
    from filewheel.converters.process_worker import _stop_owned_worker
    process = Mock(pid=1234)
    process.is_alive.side_effect = [True, True, False]
    with patch('filewheel.converters.process_worker.sys.platform', 'win32'), \
            patch('filewheel.converters.process_worker.subprocess.CREATE_NO_WINDOW', 0x08000000,
                  create=True), \
            patch('filewheel.converters.process_worker.subprocess.run') as run:
        _stop_owned_worker(process)
    command = run.call_args.args[0]
    assert command[1:] == ['/PID', '1234', '/T', '/F']
    assert Path(command[0]).name == 'taskkill.exe'
    assert run.call_args.kwargs['timeout'] == 2
    assert 'shell' not in run.call_args.kwargs
    process.kill.assert_called_once()
    process.join.assert_called_once_with(3)


def test_qt_job_cancel_of_stuck_worker_finishes_and_can_release_ui():
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtWidgets import QApplication

    from filewheel.ui.conversion_job import ConversionJob
    app = QApplication.instance() or QApplication(['cancel-worker-test'])
    app.setQuitOnLastWindowClosed(False)
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / 'source.sample'
        source.write_bytes(b'original')
        job = ConversionJob(ConversionManager(Registry((StuckEngine(),))), source, '.json')
        outcomes = []
        job.progress_changed.connect(lambda *args: job.cancelled.set())
        job.outcome.connect(lambda *args: outcomes.append(args))
        started = time.monotonic()
        job.start()
        try:
            while (job.isRunning() or not outcomes) and time.monotonic() - started < 6:
                app.processEvents()
                time.sleep(.005)
            assert not job.isRunning()
            assert len(outcomes) == 1
            assert isinstance(outcomes[0][1], ConversionCancelled)
            assert not list(Path(folder).glob('.filewheel-*'))
            assert source.read_bytes() == b'original'
        finally:
            job.cancelled.set()
            job.wait(12000)
            job.deleteLater()
            app.processEvents()


def closed_pipe_stuck_child(manager, source, extension, cancel, connection, workspace, permit):
    from filewheel.converters.process_worker import _send, configure_child
    configure_child()
    _send(connection, {'type': 'started', 'pid': os.getpid()})
    connection.close()
    time.sleep(10)


def test_cancel_deadline_also_applies_after_pipe_eof(tmp_path):
    source = tmp_path / 'source.sample'
    source.write_bytes(b'original')
    cancel = Event()
    started = time.monotonic()
    with pytest.raises(ConversionCancelled):
        run_in_process(ConversionManager(Registry((StuckEngine(),))), source, '.json',
                       cancel=cancel, progress=lambda *args: None, on_started=lambda _: cancel.set(),
                       _target=closed_pipe_stuck_child, _cancel_grace=.1)
    assert time.monotonic() - started < 5
    assert not list(tmp_path.glob('.filewheel-*'))


def test_callback_failure_can_stop_native_call_without_leaking_stage(tmp_path):
    source = tmp_path / 'source.sample'
    source.write_bytes(b'original')
    def broken_progress(*args):
        raise RuntimeError('UI callback failed')
    started = time.monotonic()
    with pytest.raises(RuntimeError, match='UI callback failed'):
        run_in_process(ConversionManager(Registry((StuckEngine(),))), source, '.json',
                       cancel=Event(), progress=broken_progress, _cancel_grace=.1)
    assert time.monotonic() - started < 5
    assert not list(tmp_path.glob('.filewheel-*'))


def test_cancel_then_tray_quit_releases_real_conversion_job(tmp_path):
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from pathlib import PureWindowsPath

    from PySide6.QtWidgets import QApplication

    from filewheel.core.models import TargetResolution
    from filewheel.ui.desktop import DesktopApplication
    app = QApplication.instance() or QApplication(['cancel-quit-test'])
    app.setQuitOnLastWindowClosed(False)
    source = tmp_path / 'source.sample'
    source.write_bytes(b'original')
    host = DesktopApplication(tray=True, manager=ConversionManager(Registry((StuckEngine(),))),
                              point_mapper=lambda point, screens: point)
    host.popup.source_mapper = lambda _: source
    target = TargetResolution(path=PureWindowsPath('C:/source.sample'), window_id=1,
                              point=(300, 300), timestamp=time.monotonic(), source='shell_explicit')
    try:
        host.popup.present(target)
        host.popup._choose(0)
        host.popup._choose(0)
        deadline = time.monotonic() + 6
        while host.popup.progress_fraction < .1 and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.005)
        assert host.popup.job is not None
        assert host.popup.progress_fraction >= .1
        host.popup._request_cancel()
        with patch.object(app, 'quit') as quit_app:
            host.request_quit()
            deadline = time.monotonic() + 6
            while host.shutdown_timer.isActive() and time.monotonic() < deadline:
                app.processEvents()
                time.sleep(.005)
            assert host.popup.job is None
            assert not host.shutdown_timer.isActive()
            quit_app.assert_called()
        assert host.popup.last_selection.action == 'conversion_cancelled'
        assert not list(tmp_path.glob('.filewheel-*'))
        assert source.read_bytes() == b'original'
    finally:
        if host.popup.job is not None:
            host.popup.job.cancelled.set()
            host.popup.job.wait(12000)
            app.processEvents()
        host.shutdown_timer.stop()
        host.popup.deleteLater()
        host.deleteLater()
        app.processEvents()


def test_os_stop_failure_retains_live_worker_stage_and_closes_reader(tmp_path):
    from types import SimpleNamespace

    cancel = Event()
    receive, send, process = Mock(), Mock(), Mock()
    receive.closed = False
    receive.poll.return_value = True
    receive.recv_bytes.return_value = b'{"type":"started","pid":777}'
    process.pid = 777
    process.is_alive.return_value = True
    context = SimpleNamespace(Pipe=lambda **kwargs: (receive, send), Event=Event,
                              Process=lambda **kwargs: process)
    with patch('filewheel.converters.process_worker._stop_owned_worker',
               side_effect=OSError('OS refused worker termination')) as stop, \
            patch.dict(os.environ, {'FILEWHEEL_LOG_DIR': str(tmp_path / 'logs')}), \
            pytest.raises(ConversionError, match='Could not stop conversion worker') as caught:
        run_in_process(ConversionManager(Registry((StuckEngine(),))), tmp_path / 'source.sample',
                       '.json', cancel=cancel, progress=lambda *args: None,
                       on_started=lambda _: cancel.set(), _context=context, _cancel_grace=0)
    assert not isinstance(caught.value, ConversionCancelled)
    assert caught.value.operation == 'stop_worker'
    assert 'OS refused worker termination' in caught.value.debug_log.read_text()
    assert len(list(tmp_path.glob('.filewheel-*'))) == 1
    stop.assert_called_once()
    receive.close.assert_called_once()
    process.close.assert_not_called()  # It is still alive; never delete beneath it.


def test_stage_cleanup_failure_is_reported_instead_of_clean_cancellation(tmp_path):
    source = tmp_path / 'source.sample'
    source.write_bytes(b'original')
    cancel = Event()
    with patch('filewheel.converters.process_worker.shutil.rmtree',
               side_effect=PermissionError('locked stage fixture')), \
            patch.dict(os.environ, {'FILEWHEEL_LOG_DIR': str(tmp_path / 'logs')}), \
            pytest.raises(ConversionError) as caught:
        run_in_process(ConversionManager(Registry((StuckEngine(),))), source, '.json',
                       cancel=cancel, progress=lambda *args: cancel.set(), _cancel_grace=.1)
    assert not isinstance(caught.value, ConversionCancelled)
    assert caught.value.operation == 'cleanup_workspace'
    assert 'locked stage fixture' in caught.value.debug_log.read_text()
    assert source.read_bytes() == b'original'
    assert not (tmp_path / 'output.json').exists()
