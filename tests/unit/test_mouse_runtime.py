"""Fake hook/COM backend verifies opt-in thread ownership and bounded shutdown."""

import copy
import json
import time
import unittest
from pathlib import Path
from threading import Event, get_ident

from filewheel.core.models import MouseEvent
from filewheel.platforms.windows.mouse_runtime import MouseRuntime


def record_fixture():
    fixture = Path(__file__).parents[1] / "fixtures/windows_sta_1_sanitized.json"
    return json.loads(fixture.read_text(encoding="utf-8"))["record"]


class FakeBackend:
    def __init__(self, record):
        self.record = record
        self.calls = []
        self.init_error = self.source_error = self.source_run_error = self.resolve_error = (
            self.close_error
        ) = None
        self.block_init = self.block_resolve = None
        self.source_stopped = Event()
        self.resolved = Event()

    def note(self, operation):
        self.calls.append((operation, get_ident()))

    def initialize(self):
        self.note("initialize")
        if self.block_init is not None:
            self.block_init.wait(2)
        if self.init_error is not None:
            raise self.init_error

    def uninitialize(self):
        self.note("uninitialize")

    def create_resolver(self, write):
        self.note("create_resolver")
        backend = self

        class Resolver:
            def resolve(self, event):
                backend.note("resolve")
                backend.resolved.set()
                if backend.block_resolve is not None:
                    backend.block_resolve.wait(2)
                if backend.resolve_error is not None:
                    raise backend.resolve_error
                write(copy.deepcopy(backend.record))

            def close(self):
                backend.note("close_resolver")
                if backend.close_error is not None:
                    raise backend.close_error

        return Resolver()

    def create_source(self, events):
        self.note("create_source")
        if self.source_error is not None:
            raise self.source_error
        backend = self

        class Source:
            def run(self, *, stop_requested):
                backend.note("run_source")
                if backend.source_run_error is not None:
                    raise backend.source_run_error
                while not stop_requested():
                    time.sleep(0.002)
                backend.source_stopped.set()

        return Source()


class MouseRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.record = record_fixture()
        self.backend = FakeBackend(self.record)
        self.candidates, self.errors = [], []
        self.runtime = MouseRuntime(
            self.candidates.append,
            self.errors.append,
            _backend=self.backend,
            _clock=lambda: self.record["timestamp_monotonic"] + 0.12,
        )

    def tearDown(self):
        if self.backend.block_init:
            self.backend.block_init.set()
        if self.backend.block_resolve:
            self.backend.block_resolve.set()
        self.runtime.close(timeout=2)

    def event(self, *, injected=False):
        return MouseEvent(
            1,
            tuple(self.record["point"]),
            self.record["timestamp_monotonic"],
            self.record["window"]["foreground_hwnd"],
            injected,
        )

    def wait(self, predicate):
        expires = time.monotonic() + 2
        while not predicate() and time.monotonic() < expires:
            time.sleep(0.002)
        self.assertTrue(predicate())

    def test_disabled_until_start_and_all_proxies_close_on_owner(self):
        self.assertFalse(self.runtime.running)
        self.assertEqual(self.backend.calls, [])
        self.assertTrue(self.runtime.start())
        self.runtime._events.put(self.event())
        self.wait(lambda: len(self.candidates) == 1)
        self.assertTrue(self.runtime.close())
        self.assertEqual(self.errors, [])
        calls = dict(self.backend.calls)
        worker = calls["initialize"]
        self.assertNotEqual(worker, get_ident())
        for operation in ("create_resolver", "resolve", "close_resolver", "uninitialize"):
            self.assertEqual(calls[operation], worker)
        self.assertEqual(calls["create_source"], calls["run_source"])
        self.assertNotEqual(calls["run_source"], worker)
        names = [name for name, _ in self.backend.calls]
        self.assertLess(names.index("close_resolver"), names.index("uninitialize"))
        self.assertTrue(self.backend.source_stopped.is_set())

    def test_gate_is_offered_before_immutable_candidate_callback(self):
        from filewheel.core.controller import InvocationController
        from filewheel.core.explicit_paths import FileCheck

        observed = []

        def candidate_callback(candidate):
            observed.append(
                self.runtime.gate.confirm(
                    candidate.token,
                    InvocationController(),
                    lambda path: FileCheck(True, True),
                    now=candidate.captured_at + 0.1,
                )
            )

        self.runtime._on_candidate = candidate_callback
        self.assertTrue(self.runtime.start())
        self.runtime._events.put(self.event())
        self.wait(lambda: len(observed) == 1)
        self.assertEqual(observed[0].target.source, "user_confirmed_candidate")

    def test_injected_and_nonexplorer_evidence_offer_nothing(self):
        self.assertTrue(self.runtime.start())
        self.runtime._events.put(self.event(injected=True))
        time.sleep(0.03)
        self.assertFalse(self.backend.resolved.is_set())
        self.backend.record["window"]["process_image"] = r"C:\unrelated.exe"
        self.runtime._events.put(self.event())
        self.wait(self.backend.resolved.is_set)
        self.assertTrue(self.runtime.close())
        self.assertEqual(self.candidates, [])

    def test_initialization_and_hook_failures_are_sanitized_and_stop(self):
        self.backend.init_error = RuntimeError("C:/private/path")
        self.assertFalse(self.runtime.start())
        self.assertTrue(self.runtime.close())
        self.assertEqual(self.errors, ["mouse_worker: RuntimeError"])
        self.assertNotIn("uninitialize", dict(self.backend.calls))

    def test_hook_factory_failure_stops_worker_and_releases_com(self):
        self.backend.source_error = OSError("private")
        self.assertFalse(self.runtime.start())
        self.assertTrue(self.runtime.close())
        self.assertEqual(self.errors, ["mouse_hook: OSError"])
        self.assertIn("uninitialize", dict(self.backend.calls))

    def test_resolver_exception_stops_listener_despite_controller_fail_closed(self):
        self.backend.resolve_error = ValueError("private")
        self.assertTrue(self.runtime.start())
        self.runtime._events.put(self.event())
        self.wait(lambda: bool(self.errors))
        self.assertTrue(self.runtime.close())
        self.assertEqual(self.errors, ["mouse_evidence: ValueError"])
        self.assertEqual(self.candidates, [])

    def test_bounded_close_discards_late_candidate_and_can_finish_later(self):
        self.backend.block_resolve = Event()
        self.assertTrue(self.runtime.start())
        self.runtime._events.put(self.event())
        self.wait(self.backend.resolved.is_set)
        self.assertFalse(self.runtime.close(timeout=0.01))
        self.backend.block_resolve.set()
        self.assertTrue(self.runtime.close(timeout=2))
        self.assertEqual(self.candidates, [])

    def test_startup_timeout_creates_no_late_resolver(self):
        self.backend.block_init = Event()
        self.assertFalse(self.runtime.start(timeout=0.01))
        self.assertFalse(self.runtime.close(timeout=0.01))
        self.backend.block_init.set()
        self.assertTrue(self.runtime.close(timeout=2))
        self.assertNotIn("create_resolver", dict(self.backend.calls))
        self.assertIn("uninitialize", dict(self.backend.calls))
        self.assertEqual(self.errors, ["mouse_startup: TimeoutError"])

    def test_cleanup_failure_is_not_reported_as_successful_shutdown(self):
        self.backend.close_error = RuntimeError("private")
        self.assertTrue(self.runtime.start())
        self.assertFalse(self.runtime.close())
        self.assertEqual(self.errors, ["mouse_cleanup: RuntimeError"])
        self.assertIn("uninitialize", dict(self.backend.calls))

    def test_candidate_callback_error_also_stops_listener(self):
        self.runtime._on_candidate = lambda candidate: (_ for _ in ()).throw(
            RuntimeError("private")
        )
        self.assertTrue(self.runtime.start())
        self.runtime._events.put(self.event())
        self.wait(lambda: bool(self.errors))
        self.assertTrue(self.runtime.close())
        self.assertEqual(self.errors, ["mouse_evidence: RuntimeError"])

    def test_hook_install_failure_after_source_creation_is_reported_and_stops(self):
        self.backend.source_run_error = OSError("private native install failure")
        self.runtime.start()
        self.wait(lambda: bool(self.errors))
        self.assertTrue(self.runtime.close())
        self.assertEqual(self.errors, ["mouse_hook: OSError"])
        self.assertFalse(self.runtime.running)
        self.assertIn("uninitialize", dict(self.backend.calls))


class ProductionComBootstrapTests(unittest.TestCase):
    def test_main_bootstrap_and_worker_reference_ownership(self):
        import sys
        import threading
        from types import SimpleNamespace
        from unittest.mock import patch

        from filewheel.platforms.windows.mouse_runtime import _WindowsMtaBackend
        calls = []
        fake = SimpleNamespace(CoInitializeEx=lambda mode: calls.append(('init', mode, threading.get_ident())),
                               CoUninitialize=lambda: calls.append(('uninit', threading.get_ident())))
        backend = _WindowsMtaBackend()
        main = threading.get_ident()
        with patch.dict(sys.modules, {'comtypes': fake}), patch('filewheel.platforms.windows.mouse_runtime.require_windows'):
            backend.prepare()
            def work():
                backend.initialize(); backend.uninitialize()
            thread = threading.Thread(target=work); thread.start(); thread.join(2)
        self.assertEqual(calls[0][0:2], ('init', 0))
        self.assertNotEqual(calls[0][2], main)
        self.assertEqual(calls[0][2], calls[1][1])
