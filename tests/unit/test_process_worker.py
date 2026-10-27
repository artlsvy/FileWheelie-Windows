"""Real spawned local conversions and bounded worker protocol tests on Windows."""
import importlib.util
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import patch

from filewheel.converters import (
    Capability,
    ConversionCancelled,
    ConversionError,
    ConversionManager,
    EngineOutput,
    Registry,
)
from filewheel.converters.images import PillowEngine
from filewheel.converters.process_worker import ProgressThrottle, decode_packet, run_in_process


class PolicyEngine:
    engine_id = 'worker-policy-fixture'
    capabilities = (Capability('.sample', 'Document', '.json', 'JSON', engine_id),)

    def available(self):
        return True

    def convert(self, source, extension, workdir, progress, cancel):
        path = workdir / 'policy.json'
        path.write_text(json.dumps({'pid': os.getpid(), 'OMP_NUM_THREADS': os.getenv('OMP_NUM_THREADS'),
                                    'OPENBLAS_NUM_THREADS': os.getenv('OPENBLAS_NUM_THREADS'),
                                    'nice': os.getpriority(os.PRIO_PROCESS, 0) if os.name != 'nt' else None}),
                        encoding='utf-8')
        return (EngineOutput(path, 'policy.json'),)

    def validate(self, output):
        json.loads(output.path.read_text())


class CancellationEngine(PolicyEngine):
    engine_id = 'worker-cancellation-fixture'
    capabilities = (Capability('.sample', 'Document', '.json', 'JSON', engine_id),)

    def convert(self, source, extension, workdir, progress, cancel):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if cancel.wait(.01):
                raise ConversionCancelled('Cancelled inside isolated converter')
        raise ConversionError('Fixture cancellation deadline exceeded')


def crash_child(manager, source, extension, cancel, connection, workspace, permit):
    os._exit(7)


def malformed_child(manager, source, extension, cancel, connection, workspace, permit):
    connection.send_bytes(b'not JSON')
    connection.close()


def oversized_child(manager, source, extension, cancel, connection, workspace, permit):
    from filewheel.converters.process_worker import MAX_PACKET_BYTES
    try:
        connection.send_bytes(b'x' * (MAX_PACKET_BYTES + 1))
    except (BrokenPipeError, OSError):
        pass
    finally:
        connection.close()


class ProcessWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.environment = patch.dict(os.environ, {'FILEWHEEL_LOG_DIR': str(self.folder / 'logs')})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.source = self.folder / 'Unicode æ input.sample'
        self.source.write_bytes(b'unchanged original')
        self.cancel = Event()

    def run_worker(self, manager, **kwargs):
        return run_in_process(manager, self.source, '.json', progress=lambda *args: None,
                              cancel=self.cancel, **kwargs)

    def test_child_pid_and_thread_limits_do_not_change_parent(self):
        before = os.environ.get('OMP_NUM_THREADS')
        pids = []
        result = self.run_worker(ConversionManager(Registry((PolicyEngine(),))), on_started=pids.append)
        report = json.loads(result.path.read_text())
        self.assertNotEqual(report['pid'], os.getpid())
        self.assertEqual(pids, [report['pid']])
        self.assertEqual(report['OMP_NUM_THREADS'], '1')
        self.assertEqual(report['OPENBLAS_NUM_THREADS'], '1')
        self.assertEqual(os.environ.get('OMP_NUM_THREADS'), before)
        self.assertEqual(self.source.read_bytes(), b'unchanged original')
        self.assertFalse(list(self.folder.glob('.filewheel-*')))

    @unittest.skipUnless(importlib.util.find_spec('PIL'), 'Pillow required')
    def test_actual_pillow_output_readable_and_source_preserved(self):
        from PIL import Image
        source = self.folder / 'real image.png'
        Image.new('RGBA', (40, 24), (100, 0, 100, 0)).save(source)
        before = source.read_bytes()
        pids, progress = [], []
        result = run_in_process(ConversionManager(Registry((PillowEngine(),))), source, '.jpg',
                                progress=lambda *args: progress.append(args), cancel=self.cancel,
                                on_started=pids.append)
        self.assertNotEqual(pids[0], os.getpid())
        with Image.open(result.path) as image:
            self.assertEqual(image.format, 'JPEG')
            self.assertEqual(image.size, (40, 24))
            self.assertEqual(image.getpixel((10, 10)), (255, 255, 255))
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(progress[-1][0], 1.)
        self.assertFalse(list(self.folder.glob('.filewheel-*')))

    @unittest.skipUnless(importlib.util.find_spec('pillow_heif'), 'HEIF codec required')
    def test_actual_heif_decoder_is_registered_in_spawned_child(self):
        import pillow_heif
        from PIL import Image
        if not pillow_heif.libheif_info().get('HEIF'):
            self.skipTest('HEIC fixture encoder unavailable')
        source = self.folder / 'heif source.heic'
        with Image.new('RGB', (32, 20), (70, 140, 210)) as image:
            pillow_heif.from_pillow(image).save(source, quality=80)
        before = source.read_bytes()
        manager = ConversionManager(Registry((PillowEngine(),)))
        result = run_in_process(manager, source, '.png', progress=lambda *args: None, cancel=self.cancel)
        with Image.open(result.path) as output:
            self.assertEqual(output.format, 'PNG')
            self.assertEqual(output.size, (32, 20))
        self.assertEqual(source.read_bytes(), before)
        self.assertFalse(list(self.folder.glob('.filewheel-*')))

    def test_actual_docx_pdf_in_spawned_child_when_libreoffice_available(self):
        from filewheel.converters.office import LibreOfficeEngine
        engine = LibreOfficeEngine(timeout=30)
        if not engine.available() or importlib.util.find_spec('docx') is None:
            self.skipTest('LibreOffice and DOCX fixture dependencies required')
        import pymupdf
        from docx import Document
        source = self.folder / 'Unicode æ office input.docx'
        document = Document()
        document.add_paragraph('Worker PDF fixture rendered locally')
        document.save(source)
        before = source.read_bytes()
        pids = []
        result = run_in_process(ConversionManager(Registry((engine,))), source, '.pdf',
                                progress=lambda *args: None, cancel=self.cancel, on_started=pids.append)
        self.assertNotEqual(pids[0], os.getpid())
        with pymupdf.open(result.path) as pdf:
            self.assertIn('Worker PDF fixture', pdf[0].get_text())
        self.assertEqual(source.read_bytes(), before)
        self.assertFalse(list(self.folder.glob('.filewheel-*')))

    def test_cancel_is_cooperative_child_exits_and_staging_is_removed(self):
        with self.assertRaises(ConversionCancelled) as caught:
            run_in_process(ConversionManager(Registry((CancellationEngine(),))), self.source, '.json',
                           progress=lambda *args: self.cancel.set(), cancel=self.cancel)
        self.assertEqual(caught.exception.engine_id, 'worker-cancellation-fixture')
        self.assertEqual(caught.exception.operation, 'convert')
        self.assertEqual(caught.exception.kind, 'conversion_cancelled')
        self.assertFalse((self.folder / 'policy.json').exists())
        self.assertFalse(list(self.folder.glob('.filewheel-*')))
        self.assertEqual(self.source.read_bytes(), b'unchanged original')

    def test_corrupt_input_preserves_engine_operation_and_child_debug_log(self):
        with self.assertRaises(ConversionError) as caught:
            run_in_process(ConversionManager(Registry((PillowEngine(),))), self.source.with_suffix('.png'), '.jpg',
                           progress=lambda *args: None, cancel=self.cancel)
        self.assertEqual(caught.exception.operation, 'validate_input')
        self.assertTrue(caught.exception.debug_log.is_file())

    def test_unexpected_exit_and_malformed_child_report_fail_without_hanging(self):
        manager = ConversionManager(Registry((PolicyEngine(),)))
        for target in (crash_child, malformed_child, oversized_child):
            with self.subTest(target=target), self.assertRaises(ConversionError):
                self.run_worker(manager, _target=target)
        self.assertEqual(self.source.read_bytes(), b'unchanged original')

    def test_precancelled_request_never_publishes(self):
        self.cancel.set()
        with self.assertRaises(ConversionCancelled):
            self.run_worker(ConversionManager(Registry((PolicyEngine(),))))
        self.assertFalse((self.folder / 'policy.json').exists())


class WorkerProtocolTests(unittest.TestCase):
    def test_malformed_messages_reject_instead_of_deserializing_arbitrary_objects(self):
        for value in (b'not JSON', b'[]', b'{"type":"progress","fraction":NaN,"message":"x"}',
                      b'{"type":"started","pid":true}',
                      b'{"type":"result","outputs":["relative"],"warnings":[],"engine_id":"x"}',
                      b'{"type":"error","category":"unknown"}'):
            with self.subTest(value=value), self.assertRaises(ConversionError):
                decode_packet(value)

    def test_flood_is_coalesced_but_final_progress_is_retained(self):
        records = []
        clock = [1.]
        report = ProgressThrottle(lambda *args: records.append(args), clock=lambda: clock[0])
        for index in range(10000):
            report(index / 10000, 'operation')
        report(1., 'finished')
        for _ in range(10000):
            report(1., 'finished')
        self.assertEqual(len(records), 2)
        self.assertEqual(records[-1], (1., 'finished'))
        clock[0] += .1
        report(.5, 'new operation')
        self.assertEqual(len(records), 3)


class BusyEngine(PolicyEngine):
    engine_id = 'worker-busy-fixture'
    capabilities = (Capability('.sample', 'Document', '.json', 'JSON', engine_id),)

    def convert(self, source, extension, workdir, progress, cancel):
        deadline = time.monotonic() + .4
        while time.monotonic() < deadline:
            if cancel.is_set():
                raise ConversionCancelled('Busy child cancelled')
        return super().convert(source, extension, workdir, progress, cancel)


class WorkerLifecycleTests(unittest.TestCase):
    def test_spawn_failure_closes_pipe_and_does_not_run_converter_in_parent(self):
        import multiprocessing
        from unittest.mock import Mock
        context = multiprocessing.get_context('spawn')
        receive, send = context.Pipe(duplex=False)
        process = Mock()
        process.start.side_effect = OSError('fixture process startup failed')
        seam = Mock()
        seam.Pipe.return_value = receive, send
        seam.Event.return_value = Event()
        seam.Process.return_value = process
        manager = Mock()
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'FILEWHEEL_LOG_DIR': directory}):
            with self.assertRaises(ConversionError) as caught:
                run_in_process(manager, Path(directory) / 'input.png', '.jpg', progress=lambda *args: None,
                               cancel=Event(), _context=seam)
            self.assertEqual(caught.exception.operation, 'start_worker')
            self.assertTrue(caught.exception.debug_log.is_file())
        manager.convert.assert_not_called()
        process.close.assert_called_once()
        self.assertTrue(receive.closed)
        self.assertTrue(send.closed)

    def test_callback_failure_requests_cleanup_and_does_not_leak_staging(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / 'input.sample'
            source.write_bytes(b'unchanged')
            def fail_callback(*args):
                raise RuntimeError('UI progress callback fixture failed')
            with self.assertRaisesRegex(RuntimeError, 'progress callback'):
                run_in_process(ConversionManager(Registry((CancellationEngine(),))), source, '.json',
                               progress=fail_callback, cancel=Event())
            self.assertFalse(list(folder.glob('.filewheel-*')))
            self.assertEqual(source.read_bytes(), b'unchanged')

    def test_qt_heartbeat_continues_during_cpu_bound_spawned_conversion(self):
        try:
            from PySide6.QtCore import QTimer
            from PySide6.QtWidgets import QApplication

            from filewheel.ui.conversion_job import ConversionJob
        except ImportError:
            self.skipTest('PySide6 required')
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        app = QApplication.instance() or QApplication(['process-heartbeat'])
        app.setQuitOnLastWindowClosed(False)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.sample'
            source.write_bytes(b'unchanged')
            manager = ConversionManager(Registry((BusyEngine(),)))
            job = ConversionJob(manager, source, '.json')
            outcomes, ticks = [], []
            job.outcome.connect(lambda *args: outcomes.append(args))
            timer = QTimer()
            timer.setInterval(10)
            timer.timeout.connect(lambda: ticks.append(time.monotonic()))
            timer.start()
            try:
                job.start()
                deadline = time.monotonic() + 5
                while (job.isRunning() or not outcomes) and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(.003)
                self.assertFalse(job.isRunning())
                self.assertEqual(len(outcomes), 1)
                self.assertIsNone(outcomes[0][1])
                self.assertNotEqual(job.worker_pid, os.getpid())
                self.assertGreaterEqual(len(ticks), 5)
                self.assertEqual(source.read_bytes(), b'unchanged')
            finally:
                timer.stop()
                job.cancelled.set()
                job.wait(5000)
                job.deleteLater()
                app.processEvents()


def windows_pipe_error(code):
    error = OSError(f'fixture Windows pipe error {code}')
    error.winerror = code
    return error


class WindowsEndedReader:
    """Simulate Windows poll closure after a real spawned child's outcome."""
    def __init__(self, connection):
        self.connection = connection
        self.terminal = False

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def poll(self, timeout):
        if self.terminal:
            raise windows_pipe_error(109)
        return self.connection.poll(timeout)

    def recv_bytes(self, maximum):
        payload = self.connection.recv_bytes(maximum)
        self.terminal = decode_packet(payload)['type'] in ('result', 'error')
        return payload


class WindowsEndedContext:
    def __init__(self):
        import multiprocessing
        self.context = multiprocessing.get_context('spawn')

    def __getattr__(self, name):
        return getattr(self.context, name)

    def Pipe(self, *, duplex):
        receive, send = self.context.Pipe(duplex=duplex)
        return WindowsEndedReader(receive), send


class WindowsPipeEofTests(unittest.TestCase):
    def test_real_conversion_with_windows_poll_eof_keeps_success_and_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'input.sample'
            source.write_bytes(b'unchanged source')
            result = run_in_process(ConversionManager(Registry((PolicyEngine(),))), source, '.json',
                                    progress=lambda *args: None, cancel=Event(),
                                    _context=WindowsEndedContext())
            self.assertNotEqual(json.loads(result.path.read_text())['pid'], os.getpid())
            self.assertEqual(source.read_bytes(), b'unchanged source')
            self.assertFalse(list(Path(folder).glob('.filewheel-*')))

    def run_script(self, messages, *, exitcode=0, poll_error=109):
        from types import SimpleNamespace
        from unittest.mock import Mock

        from filewheel.converters import process_worker as worker
        remaining = list(messages)
        receive, send, process = Mock(), Mock(), Mock()
        receive.closed = False
        def close_reader():
            receive.closed = True
        receive.close.side_effect = close_reader
        def poll(timeout):
            if remaining:
                return True
            raise windows_pipe_error(poll_error)
        receive.poll.side_effect = poll
        def read(maximum):
            value = remaining.pop(0)
            if isinstance(value, Exception):
                raise value
            return value if isinstance(value, bytes) else json.dumps(value).encode()
        receive.recv_bytes.side_effect = read
        process.pid, process.exitcode = 777, exitcode
        process.is_alive.return_value = False
        context = SimpleNamespace(Pipe=lambda **kwargs: (receive, send), Event=Event,
                                  Process=lambda **kwargs: process)
        try:
            return worker.run_in_process(ConversionManager(Registry((PolicyEngine(),))),
                                         Path(self.folder) / 'input.sample', '.json',
                                         progress=lambda *args: None, cancel=Event(), _context=context)
        finally:
            self.assertTrue(receive.closed)
            send.close.assert_called()
            process.join.assert_called_once()
            process.close.assert_called_once()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = self.temporary.name
        environment = patch.dict(os.environ, {'FILEWHEEL_LOG_DIR': str(Path(self.folder) / 'logs')})
        environment.start()
        self.addCleanup(environment.stop)
        self.start = {'type': 'started', 'pid': 777}
        self.result = {'type': 'result', 'outputs': [str(Path(self.folder) / 'output.json')],
                       'warnings': ['Preserved warning'], 'engine_id': PolicyEngine.engine_id}

    def test_valid_terminal_and_zero_exit_survive_closed_poll(self):
        result = self.run_script([self.start, {'type': 'publish_ready'}, self.result])
        self.assertEqual(result.engine_id, PolicyEngine.engine_id)
        self.assertEqual(result.warnings, ('Preserved warning',))

    def test_close_without_terminal_or_after_crash_cannot_claim_success(self):
        Path(self.result['outputs'][0]).write_text('{}')  # Existing output is not an outcome receipt.
        for messages, code in (([], 0), ([self.start], 0), ([self.start, {'type': 'publish_ready'}, self.result], 7)):
            with self.subTest(messages=messages, exitcode=code), self.assertRaises(ConversionError):
                self.run_script(messages, exitcode=code)

    def test_real_error_categories_survive_normal_pipe_closure(self):
        from filewheel.converters.base import DependencyUnavailable
        for category, expected in (('conversion', ConversionError), ('cancelled', ConversionCancelled),
                                    ('dependency', DependencyUnavailable)):
            error = {'type': 'error', 'category': category, 'message': 'Actual engine failure',
                     'engine_id': 'test-engine', 'operation': 'convert', 'kind': 'test-kind',
                     'debug_log': str(Path(self.folder) / 'worker-debug.log')}
            with self.subTest(category=category), self.assertRaises(expected) as caught:
                self.run_script([self.start, error])
            self.assertEqual(str(caught.exception), 'Actual engine failure')
            self.assertEqual(caught.exception.engine_id, 'test-engine')
            self.assertEqual(caught.exception.operation, 'convert')

    def test_other_poll_errors_and_read_errors_are_not_normalized_to_success(self):
        for mode in ('access_denied', 'broken_read', 'partial_read', 'malformed_protocol', 'extra_terminal'):
            messages, poll_error = [self.start, {'type': 'publish_ready'}, self.result], 109
            if mode == 'access_denied':
                poll_error = 5
            elif mode == 'broken_read':
                messages.append(windows_pipe_error(109))
            elif mode == 'partial_read':
                messages.append(OSError('got end of file during message'))
            elif mode == 'malformed_protocol':
                messages = [self.start, b'not JSON', self.result]
            else:
                messages.append(self.result)
            with self.subTest(mode=mode), self.assertRaises(ConversionError):
                self.run_script(messages, poll_error=poll_error)
