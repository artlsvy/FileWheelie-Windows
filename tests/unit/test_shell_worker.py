"""Apartment ownership/timeout tests with fakes; not Windows integration proof."""

import threading
import unittest

from filewheel.platforms.windows.shell_worker import ShellStaWorker


class Backend:
    def __init__(self):
        self.calls = []

    def initialize(self):
        self.calls.append(("initialize", threading.get_ident()))

    def pump(self):
        self.calls.append(("pump", threading.get_ident()))

    def uninitialize(self):
        self.calls.append(("uninitialize", threading.get_ident()))


class ShellWorkerTests(unittest.TestCase):
    def test_collector_lifecycle_and_apartment_run_on_owner_thread(self):
        backend = Backend()
        calls = []
        class Collector:
            def __init__(self):
                calls.append(("factory", threading.get_ident()))

            def collect(self, hwnd, ancestry):
                calls.append(("collect", threading.get_ident()))
                return {"hwnd": hwnd, "ancestry": ancestry}

            def close(self):
                calls.append(("close", threading.get_ident()))

        worker = ShellStaWorker(Collector, _backend=backend)
        try:
            source = [{"name": "A"}]
            result = worker.collect(123, source)
            self.assertEqual(result, {"hwnd": 123, "ancestry": source})
            self.assertIsNot(result["ancestry"], source)
        finally:
            self.assertTrue(worker.close())
        owner = calls[0][1]
        self.assertNotEqual(owner, threading.get_ident())
        self.assertTrue(all(thread == owner for _, thread in calls + backend.calls))
        self.assertEqual([name for name, _ in calls], ["factory", "collect", "close"])
        self.assertEqual(backend.calls[0][0], "initialize")
        self.assertEqual(backend.calls[-1][0], "uninitialize")

    def test_opaque_request_and_result_objects_never_cross_boundary(self):
        class Collector:
            def collect(self, hwnd, ancestry):
                return {"opaque": object()}

            def close(self):
                pass

        worker = ShellStaWorker(Collector, _backend=Backend())
        try:
            for ancestry in ([{"opaque": object()}], [{1: "non-string key"}], [float("nan")]):
                with self.subTest(ancestry=ancestry), self.assertRaises(ValueError):
                    worker.collect(123, ancestry)
            with self.assertRaisesRegex(RuntimeError, "^Shell STA collection failed$"):
                worker.collect(123, [])
        finally:
            self.assertTrue(worker.close())

    def test_request_exception_is_sanitized_and_worker_can_continue(self):
        class Collector:
            def collect(self, hwnd, ancestry):
                if hwnd == 1:
                    raise RuntimeError("private filename")
                return {"ok": True}

            def close(self):
                pass

        worker = ShellStaWorker(Collector, _backend=Backend())
        try:
            with self.assertRaisesRegex(RuntimeError, "^Shell STA collection failed$"):
                worker.collect(1, [])
            self.assertEqual(worker.collect(2, []), {"ok": True})
        finally:
            self.assertTrue(worker.close())

    def test_timed_out_reply_is_not_reused_for_later_request(self):
        entered = threading.Event()
        release = threading.Event()
        class Collector:
            def collect(self, hwnd, ancestry):
                if hwnd == 1:
                    entered.set()
                    release.wait(2)
                return {"hwnd": hwnd}

            def close(self):
                pass

        worker = ShellStaWorker(Collector, _backend=Backend())
        try:
            with self.assertRaises(TimeoutError):
                worker.collect(1, [], timeout=0.03)
            self.assertTrue(entered.is_set())
            release.set()
            self.assertEqual(worker.collect(2, [], timeout=1), {"hwnd": 2})
        finally:
            release.set()
            self.assertTrue(worker.close())

    def test_busy_provider_has_bounded_queue_and_shutdown(self):
        entered = threading.Event()
        release = threading.Event()
        class Collector:
            def collect(self, hwnd, ancestry):
                entered.set()
                release.wait(2)
                return {"ok": True}

            def close(self):
                pass

        worker = ShellStaWorker(Collector, _backend=Backend())
        try:
            with self.assertRaises(TimeoutError):
                worker.collect(1, [], timeout=0.03)
            self.assertTrue(entered.is_set())
            with self.assertRaises(TimeoutError):
                worker.collect(2, [], timeout=0.03)
            with self.assertRaisesRegex(TimeoutError, "queue is full"):
                worker.collect(3, [], timeout=0.03)
            self.assertFalse(worker.close(timeout=0.01))
            with self.assertRaises(RuntimeError):
                worker.collect(4, [])
        finally:
            release.set()
            self.assertTrue(worker.close())

    def test_factory_failure_uninitializes_and_hides_error_text(self):
        backend = Backend()
        def fail():
            raise RuntimeError("private startup info")
        with self.assertRaisesRegex(RuntimeError, "^Shell STA startup failed$"):
            ShellStaWorker(fail, _backend=backend)
        # Startup failure is signaled before finalization; wait for its cleanup.
        for _ in range(100):
            if any(name == "uninitialize" for name, _ in backend.calls):
                break
            threading.Event().wait(0.001)
        self.assertEqual(backend.calls[-1][0], "uninitialize")

    def test_cleanup_failure_is_reported_without_releasing_on_caller(self):
        class Collector:
            def collect(self, hwnd, ancestry):
                return {}

            def close(self):
                raise RuntimeError("private cleanup info")

        backend = Backend()
        worker = ShellStaWorker(Collector, _backend=backend)
        self.assertFalse(worker.close())
        self.assertEqual(backend.calls[-1][0], "uninitialize")

    def test_rejected_opaque_result_is_destroyed_before_uninitialize(self):
        lifecycle = []
        class Opaque:
            def __del__(self):
                lifecycle.append(("destroy", threading.get_ident()))

        class Collector:
            def collect(self, hwnd, ancestry):
                return {"proxy": Opaque()}

            def close(self):
                lifecycle.append(("close", threading.get_ident()))

        class LifetimeBackend(Backend):
            def uninitialize(self):
                lifecycle.append(("uninitialize", threading.get_ident()))
                super().uninitialize()

        worker = ShellStaWorker(Collector, _backend=LifetimeBackend())
        with self.assertRaises(RuntimeError):
            worker.collect(1, [])
        self.assertTrue(worker.close())
        self.assertEqual([name for name, _ in lifecycle], ["destroy", "close", "uninitialize"])
        self.assertTrue(all(thread != threading.get_ident() for _, thread in lifecycle))

    def test_abandoned_startup_skips_factory_and_uninitializes(self):
        release = threading.Event()
        finished = threading.Event()
        class SlowBackend(Backend):
            def initialize(self):
                super().initialize()
                release.wait(2)

            def uninitialize(self):
                super().uninitialize()
                finished.set()

        def factory():
            self.fail("factory must not run after startup timeout")

        backend = SlowBackend()
        try:
            with self.assertRaisesRegex(TimeoutError, "^Shell STA startup timed out$"):
                ShellStaWorker(factory, _backend=backend, startup_timeout=0.01)
        finally:
            release.set()
        self.assertTrue(finished.wait(1))

    def test_nonfinite_startup_and_shutdown_timeouts_are_rejected(self):
        for timeout in (None, float("inf"), float("nan"), -1):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                ShellStaWorker(lambda: None, _backend=Backend(), startup_timeout=timeout)
