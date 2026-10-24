"""Test apartment routing with DTO fakes, not real COM initialization or behavior."""

import unittest
from types import SimpleNamespace

from filewheel.core.probe_errors import ProbeFailure, probe_step
from filewheel.platforms.windows.explorer_resolver import ExplorerTargetResolver


class ShellApartmentIntegrationTests(unittest.TestCase):
    def test_dry_run_delegates_shell_evidence_to_owner_worker(self):
        resolver = object.__new__(ExplorerTargetResolver)
        calls = []
        resolver._shell_worker = SimpleNamespace(collect=lambda *args: calls.append(args) or {"ok": 1})
        resolver._shell_collector = None
        self.assertEqual(resolver._shell_evidence(123, [{"name": "A"}]), {"ok": 1})
        self.assertEqual(calls, [(123, [{"name": "A"}])])

    def test_default_diagnostic_keeps_existing_collector_route(self):
        resolver = object.__new__(ExplorerTargetResolver)
        resolver._shell_worker = None
        resolver._shell_collector = SimpleNamespace(collect=lambda hwnd, ancestry: {"hwnd": hwnd})
        self.assertEqual(resolver._shell_evidence(123), {"hwnd": 123})

    def test_cleanup_timeout_does_not_leave_uia_proxy_referenced(self):
        resolver = object.__new__(ExplorerTargetResolver)
        resolver._automation = object()
        resolver._shell_collector = None
        resolver._shell_worker = SimpleNamespace(close=lambda: False)
        with self.assertRaises(TimeoutError):
            resolver.close()
        self.assertIsNone(resolver._automation)

    def test_observed_input_sync_hresult_is_named(self):
        class CapturedCOMError(Exception):
            hresult = -2147417843

        def fail():
            raise CapturedCOMError()

        with self.assertRaises(ProbeFailure) as caught:
            probe_step([], "get_active_view_hwnd", fail)
        self.assertEqual(caught.exception.evidence["hresult_hex"], "0x8001010D")
        self.assertEqual(caught.exception.evidence["hresult_name"], "RPC_E_CANTCALLOUT_ININPUTSYNCCALL")
