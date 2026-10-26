"""Spawned conversion isolation; no Qt/COM objects cross this local boundary.

The GUI's Python mouse-hook callbacks must not compete with converter code for
one interpreter GIL. The existing ConversionManager still owns staging,
validation and no-replacement publication in the child process. The parent owns
staging cleanup and may stop a stuck encoder before granting publication.
"""

import json
import math
import multiprocessing
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from time import monotonic

from filewheel.converters.base import (
    ConversionCancelled,
    ConversionError,
    ConversionResult,
    DependencyUnavailable,
    check_cancel,
)
from filewheel.converters.debugging import record_failure

MAX_PACKET_BYTES = 16 * 1024 * 1024
MAX_OUTPUTS = 10000
_THREAD_LIMITS = (
    'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
    'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'BLIS_NUM_THREADS',
    'OPENCV_FOR_THREADS_NUM',
)


def configure_child():
    """Limit common native pools before lazy engine imports; parent is unchanged."""
    for variable in _THREAD_LIMITS:
        os.environ[variable] = '1'
    os.environ['ORT_DISABLE_TELEMETRY'] = '1'
    # Native libraries have additional private pools; this is not a guarantee
    # that every third-party library uses exactly one thread.
    try:
        if sys.platform == 'win32':
            import ctypes as c
            from ctypes import wintypes as w
            kernel = c.WinDLL('kernel32', use_last_error=True)
            kernel.GetCurrentProcess.argtypes = []
            kernel.GetCurrentProcess.restype = w.HANDLE
            kernel.SetPriorityClass.argtypes = [w.HANDLE, w.DWORD]
            kernel.SetPriorityClass.restype = w.BOOL
            kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000)  # BELOW_NORMAL
        else:
            os.setsid()  # An owned group for cancellation, never the tray/UI group.
            os.nice(5)
    except OSError:
        pass  # Best-effort scheduling; isolation remains effective without it.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')  # noqa: SIM115 - child lifetime
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')  # noqa: SIM115 - child lifetime


def _send(connection, packet):
    encoded = json.dumps(packet, ensure_ascii=True, allow_nan=False).encode('utf-8')
    if len(encoded) > MAX_PACKET_BYTES:
        raise ConversionError('Conversion report exceeds the local message limit')
    connection.send_bytes(encoded)


class ProgressThrottle:
    """Coalesce frequent backend updates rather than flooding the Qt event queue."""
    def __init__(self, report, *, clock=monotonic, interval=.05):
        self.report, self.clock, self.interval = report, clock, interval
        self.last = -float('inf')
        self.last_fraction = None

    def __call__(self, fraction, message):
        if type(fraction) not in (int, float) or not math.isfinite(fraction):
            return
        fraction = max(0., min(1., fraction))
        now = self.clock()
        if now - self.last >= self.interval or fraction == 1. and self.last_fraction != 1.:
            self.last = now
            self.last_fraction = fraction
            self.report(fraction, str(message)[:2048])


def _error_packet(error):
    category = ('cancelled' if isinstance(error, ConversionCancelled) else
                'dependency' if isinstance(error, DependencyUnavailable) else 'conversion')
    default_kind = {'cancelled': 'conversion_cancelled', 'dependency': 'dependency_unavailable',
                    'conversion': 'conversion_failed'}[category]
    return {'type': 'error', 'category': category, 'message': str(error)[:16000],
            'engine_id': str(getattr(error, 'engine_id', 'unselected'))[:256],
            'operation': str(getattr(error, 'operation', 'worker'))[:256],
            'kind': str(getattr(error, 'kind', default_kind))[:256],
            'debug_log': str(getattr(error, 'debug_log', '') or '')[:32767]}


def _prepare_codecs(manager, source, extension):
    # Pillow opener registration is process-local and does not survive spawn.
    # Preserve the caller's registry/options; only restore the selected codec.
    if Path(source).suffix.lower() in ('.heic', '.heif'):
        capability = manager.registry.find(Path(source).suffix, extension)
        if capability.engine_id == 'pillow':
            try:
                from pillow_heif import register_heif_opener
                register_heif_opener(thumbnails=False)
            except ImportError as error:
                failure = DependencyUnavailable('HEIF decoder is unavailable in conversion worker')
                failure.engine_id, failure.operation = 'pillow', 'initialize_decoder'
                failure.kind = 'dependency_unavailable'
                failure.debug_log = record_failure('pillow', 'initialize_decoder', error)
                raise failure from error


def _child(manager, source, extension, cancellation, connection, workspace, publication_permit):
    """Top-level spawn target; imports only local engine logic, never the GUI."""
    configure_child()
    try:
        _send(connection, {'type': 'started', 'pid': os.getpid()})
        progress = ProgressThrottle(lambda fraction, message: _send(
            connection, {'type': 'progress', 'fraction': fraction, 'message': message}))
        try:
            _prepare_codecs(manager, source, extension)
            def before_publish():
                _send(connection, {'type': 'publish_ready'})
                while not publication_permit.wait(.05):
                    check_cancel(cancellation)
                check_cancel(cancellation)
            result = manager.convert(Path(source), extension, progress=progress, cancel=cancellation,
                                     workspace=Path(workspace), before_publish=before_publish)
        except Exception as error:  # noqa: BLE001 - child boundary reports real engine failures
            if not isinstance(error, ConversionError):
                error.debug_log = record_failure('worker', 'convert', error)
            _send(connection, _error_packet(error))
        else:
            _send(connection, {'type': 'result', 'outputs': [str(path) for path in result.outputs],
                               'warnings': list(result.warnings), 'engine_id': result.engine_id})
    except (OSError, ValueError, ConversionError) as error:
        # If reporting failed, do not claim rollback: publication may already
        # have completed. Parent reports an interrupted worker and retains logs.
        record_failure('worker', 'report_outcome', error)
    finally:
        connection.close()


def decode_packet(payload):
    """Strict bounded JSON validation; no remote or pickle-based result protocol."""
    if not isinstance(payload, bytes) or len(payload) > MAX_PACKET_BYTES:
        raise ConversionError('Invalid conversion worker report')
    try:
        packet = json.loads(payload)
    except (UnicodeError, ValueError) as error:
        raise ConversionError('Invalid conversion worker report') from error
    if not isinstance(packet, dict):
        raise ConversionError('Invalid conversion worker report')
    kind = packet.get('type')
    valid = False
    if kind == 'started':
        valid = set(packet) == {'type', 'pid'} and type(packet['pid']) is int and packet['pid'] > 0
    elif kind == 'publish_ready':
        valid = set(packet) == {'type'}
    elif kind == 'progress':
        value = packet.get('fraction')
        valid = (set(packet) == {'type', 'fraction', 'message'}
                 and type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1
                 and isinstance(packet['message'], str) and len(packet['message']) <= 2048)
    elif kind == 'result':
        valid = (set(packet) == {'type', 'outputs', 'warnings', 'engine_id'}
                 and isinstance(packet['outputs'], list) and 0 < len(packet['outputs']) <= MAX_OUTPUTS
                 and all(isinstance(path, str) and 0 < len(path) <= 32767 and Path(path).is_absolute()
                         for path in packet['outputs'])
                 and isinstance(packet['warnings'], list) and len(packet['warnings']) <= 1000
                 and all(isinstance(item, str) and len(item) <= 16000 for item in packet['warnings'])
                 and isinstance(packet['engine_id'], str) and 0 < len(packet['engine_id']) <= 256)
    elif kind == 'error':
        keys = {'type', 'category', 'message', 'engine_id', 'operation', 'kind', 'debug_log'}
        valid = (set(packet) == keys and packet.get('category') in ('cancelled', 'dependency', 'conversion')
                 and all(isinstance(packet[key], str) and len(packet[key]) <= limit for key, limit in
                         (('message', 16000), ('engine_id', 256), ('operation', 256),
                          ('kind', 256), ('debug_log', 32767))))
    if not valid:
        raise ConversionError('Invalid conversion worker report')
    return packet


def _raise_reported_error(packet):
    kind = {'cancelled': ConversionCancelled, 'dependency': DependencyUnavailable,
            'conversion': ConversionError}[packet['category']]
    error = kind(packet['message'])
    error.engine_id, error.operation = packet['engine_id'], packet['operation']
    error.kind = packet['kind']
    error.debug_log = Path(packet['debug_log']) if packet['debug_log'] else None
    raise error


def _supervisor_failure(error, manager, source, extension, operation):
    engine = 'worker'
    try:
        engine = manager.registry.find(Path(source).suffix, extension).engine_id
    except (AttributeError, ConversionError):
        pass
    error.engine_id, error.operation = engine, operation
    error.kind = 'conversion_failed'
    error.debug_log = record_failure(engine, operation, error)
    return error


def _poll_reader(connection, timeout):
    """Normalize a closed Windows pipe at the polling boundary only.

    CPython's Windows PipeConnection.poll() calls PeekNamedPipe, which may
    raise ERROR_BROKEN_PIPE rather than making recv_bytes() raise EOFError.
    Read errors (including partial frames) must keep their failure semantics.
    """
    try:
        return connection.poll(timeout)
    except OSError as error:
        if getattr(error, 'winerror', None) == 109:  # ERROR_BROKEN_PIPE
            raise EOFError from error
        raise


def _stop_owned_worker(process):
    """Stop this still-owned child's tree before publication; never by image name."""
    if not process.is_alive():
        return
    if sys.platform == 'win32':
        executable = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'taskkill.exe'
        try:
            subprocess.run([str(executable), '/PID', str(process.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=2, check=False,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            # The child calls setsid before importing any conversion engine.
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass  # Cancellation during startup, before setsid.
    if process.is_alive():
        process.kill()
    process.join(3)
    if process.is_alive():
        raise ConversionError('Conversion worker could not be stopped; close Filewheel and retry')


def run_in_process(manager, source, extension, *, progress, cancel, on_started=None,
                   _context=None, _target=_child, _cancel_grace=2.):
    """Supervise one owned child off the GUI thread, then return after it exits.

    Give cancellation a short grace period, then stop a stuck encoder. Publication
    requires a parent permit; after granting it, termination is forbidden so the
    manager can finish or roll back its atomic links. Outcome follows cleanup.
    """
    check_cancel(cancel)
    context = multiprocessing.get_context('spawn') if _context is None else _context
    receive, send = context.Pipe(duplex=False)
    child_cancel = context.Event()
    publication_permit = context.Event()
    workspace = Path(tempfile.mkdtemp(prefix='.filewheel-', dir=Path(source).parent))
    process = context.Process(target=_target, args=(manager, str(source), extension, child_cancel, send,
                                                  str(workspace), publication_permit),
                              name='filewheel-conversion')
    terminal = failure = None
    started = False
    seen_started = False
    publication_allowed = publish_ready = forced_cancel = False
    stop_failed = False
    stopping_since = None

    def stop_if_overdue():
        nonlocal stopping_since, forced_cancel, stop_failed
        if cancel.is_set() or child_cancel.is_set():
            child_cancel.set()
            if stopping_since is None:
                stopping_since = monotonic()
            if not publication_allowed and monotonic() - stopping_since >= _cancel_grace:
                try:
                    _stop_owned_worker(process)
                except (OSError, ConversionError) as error:
                    stop_failed = True
                    failure = ConversionError('Could not stop conversion worker; temporary files retained')
                    failure.__cause__ = error
                    raise _supervisor_failure(failure, manager, source, extension, 'stop_worker') from error
                forced_cancel = True
                return True
        return False

    try:
        check_cancel(cancel)
        try:
            process.start()
        except Exception as error:  # No unsafe shared-process fallback.
            failure = ConversionError('Could not start isolated conversion worker')
            failure.engine_id, failure.operation = 'worker', 'start_worker'
            failure.debug_log = record_failure('worker', 'start_worker', error)
            raise failure from error
        started = True
        send.close()  # EOF must depend on the child's writer, not our duplicate.
        while True:
            if stop_if_overdue():
                break
            if receive.closed:
                if not process.is_alive():
                    break
                process.join(.05)
                continue
            try:
                ready = _poll_reader(receive, .05)
            except EOFError:
                receive.close()
                continue  # Remain cancellable while waiting for the child's exit.
            except OSError as error:
                failure = ConversionError('Conversion worker pipe polling failed')
                failure.__cause__ = error
                child_cancel.set()
                receive.close()
                continue
            if ready:
                try:
                    payload = receive.recv_bytes(MAX_PACKET_BYTES)
                except EOFError:
                    receive.close()
                    continue
                except OSError:
                    failure = ConversionError('Conversion worker report was interrupted')
                    child_cancel.set()
                    receive.close()  # Wake a writer blocked on an oversized/broken packet.
                    continue
                if failure is not None:
                    continue  # Drain after a protocol failure without dispatching more callbacks.
                try:
                    packet = decode_packet(payload)
                    kind = packet['type']
                    if terminal is not None:
                        raise ConversionError('Unexpected report after conversion outcome')
                    if kind == 'started':
                        if seen_started or packet['pid'] != process.pid:
                            raise ConversionError('Conversion worker identity mismatch')
                        seen_started = True
                        if on_started is not None:
                            on_started(packet['pid'])
                    elif not seen_started:
                        raise ConversionError('Conversion worker did not identify itself')
                    elif kind == 'progress':
                        progress(packet['fraction'], packet['message'])
                    elif kind == 'publish_ready':
                        if publish_ready:
                            raise ConversionError('Duplicate publication request')
                        publish_ready = True
                        if not cancel.is_set():
                            publication_allowed = True
                            publication_permit.set()
                    else:
                        if kind == 'result' and not publication_allowed:
                            raise ConversionError('Conversion result without publication permission')
                        terminal = packet
                except ConversionError as error:
                    failure = error
                    child_cancel.set()
            elif not process.is_alive():
                break
        process.join()  # Outcome is emitted only after owned-child cleanup/exit.
        if failure is not None:
            raise _supervisor_failure(failure, manager, source, extension, 'worker_protocol')
        if forced_cancel:
            error = ConversionCancelled('Conversion cancelled')
            try:
                error.engine_id = manager.registry.find(Path(source).suffix, extension).engine_id
            except (AttributeError, ConversionError):
                error.engine_id = 'worker'
            error.operation, error.kind = 'convert', 'conversion_cancelled'
            raise error
        if process.exitcode != 0 or terminal is None:
            failure = ConversionError(
                f'Conversion worker exited unexpectedly (code {process.exitcode}); '
                'inspect output folder and debug log')
            raise _supervisor_failure(failure, manager, source, extension, 'worker_exit')
        if terminal['type'] == 'error':
            _raise_reported_error(terminal)
        return ConversionResult(tuple(Path(path) for path in terminal['outputs']),
                                tuple(terminal['warnings']), terminal['engine_id'])
    finally:
        send.close()
        try:
            if started and not stop_failed and process.is_alive():
                child_cancel.set()
                # Drain reports during cancellation so a reporting child cannot
                # deadlock on a full pipe. The same pre-publication deadline applies.
                while process.is_alive():
                    if stop_if_overdue():
                        break
                    if receive.closed:
                        process.join(.05)
                    else:
                        try:
                            if _poll_reader(receive, .05):
                                receive.recv_bytes(MAX_PACKET_BYTES)
                        except (OSError, EOFError, ValueError):
                            receive.close()
                process.join()
        finally:
            receive.close()
            if not started or not process.is_alive():
                process.close()
                try:
                    shutil.rmtree(workspace)
                except OSError as error:
                    failure = ConversionError('Could not remove conversion temporary files')
                    failure.__cause__ = error
                    raise _supervisor_failure(
                        failure, manager, source, extension, 'cleanup_workspace') from error
        # If the OS refuses termination, retain staging: never delete files
        # beneath a live converter. The caller receives a cleanup failure.
