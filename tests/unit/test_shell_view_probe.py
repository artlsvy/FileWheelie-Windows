"""Probe control flow and ownership with fakes; these do not verify native ABI."""

import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch

from filewheel.platforms.windows.diagnostics import mapping_console_line
from filewheel.platforms.windows.shell_view import ShellViewProbe


def probe_and_window(*, associated=True, changed=False):
    probe = object.__new__(ShellViewProbe)
    freed = []
    probe._ole = NS(CoTaskMemFree=freed.append)
    ancestry = [
        {"class_name": "UIItemsView", "native_hwnd": 40},
        {"class_name": "ShellTabWindowClass", "native_hwnd": 20},
        {"class_name": "CabinetWClass", "native_hwnd": 10},
    ]
    folder = NS(
        ItemCount=lambda flags: 3, GetItem=lambda index, iid: NS(
            GetAttributes=lambda flags: 0x40000000,
        ),
        Item=lambda index: "allocated-pidl", GetItemPosition=lambda pidl: NS(x=1, y=2),
        GetCurrentViewMode=lambda: 1,
    )
    view = NS(GetWindow=lambda: 30, QueryInterface=lambda kind: folder)
    later_view = NS(GetWindow=lambda: 31 if changed else 30)
    views = iter([view, later_view])
    browser = NS(QueryActiveShellView=lambda: next(views), GetWindow=lambda: 20)
    unknown = NS(QueryInterface=lambda kind: browser)
    service = NS(QueryService=lambda service, iid: unknown)
    window = NS(QueryInterface=lambda kind: service)
    probe._native = NS(kernel=NS(GetDriveTypeW=lambda root: 3), user=NS(
        IsChild=lambda parent, child: associated and (parent, child) in ((20, 30), (30, 40)),
        GetAncestor=lambda hwnd, flags: 10,
        ClientToScreen=lambda hwnd, point: True,
    ))
    interface = NS(_iid_=object())
    probe._types = (NS(byref=lambda value: value), object(), lambda value: value,
                    interface, interface, interface, interface)
    probe._path = lambda item: "C:/fixture/a.txt"
    return probe, window, ancestry, freed


class ShellViewProbeTests(unittest.TestCase):
    def test_service_failure_reports_exact_stage_and_hresult_without_message(self):
        class FakeCOMError(Exception):
            hresult = -2147467262

        probe, window, ancestry, _ = probe_and_window()
        service = window.QueryInterface(None)
        def fail(*args):
            raise FakeCOMError("private filename must not enter the log")
        service.QueryService = fail
        report = probe.capture(window, ancestry, 1)
        failure = report["active_view_association"]
        self.assertEqual(failure["status"], "unproven")
        self.assertEqual(failure["stage"], "query_top_level_browser_service")
        self.assertEqual(failure["hresult_hex"], "0x80004002")
        self.assertEqual(failure["hresult_name"], "E_NOINTERFACE")
        self.assertEqual(failure["completed_stages"], ["query_service_provider"])
        self.assertNotIn("private filename", str(report))
        self.assertNotIn("native_view_candidate", report)

    def test_later_path_failure_does_not_get_relabeled_as_service_failure(self):
        probe, window, ancestry, _ = probe_and_window()
        def fail(item):
            raise OSError("private")
        probe._path = fail
        failure = probe.capture(window, ancestry, 1)["active_view_association"]
        self.assertEqual(failure["stage"], "get_filesystem_path")
        self.assertIn("get_indexed_shell_item", failure["completed_stages"])
        self.assertIsNone(failure["hresult"])

    def test_observed_hwnd_chain_and_path_are_candidate_evidence_only(self):
        probe, window, ancestry, freed = probe_and_window()
        with patch("filewheel.platforms.windows.shell_view.os.stat", return_value=NS(
            st_mode=0o100644, st_file_attributes=0,
        )):
            result = probe.capture(window, ancestry, 1)
        self.assertEqual(result["active_view_association"]["status"], "matched")
        self.assertFalse(result["active_view_association"]["windows_verified"])
        self.assertTrue(result["native_view_candidate"]["snapshot_stable"])
        self.assertTrue(result["native_view_candidate"]["exists_regular_file"])
        self.assertEqual(freed, ["allocated-pidl"])

    def test_wrong_tab_chain_collects_no_native_item_path(self):
        probe, window, ancestry, freed = probe_and_window(associated=False)
        probe._path = lambda item: self.fail("unassociated view path read")
        result = probe.capture(window, ancestry, 1)
        self.assertEqual(result["active_view_association"]["status"], "unproven")
        self.assertNotIn("native_view_candidate", result)
        self.assertFalse(freed)

    def test_view_change_is_explicitly_unstable(self):
        probe, window, ancestry, _ = probe_and_window(changed=True)
        with patch("filewheel.platforms.windows.shell_view.os.stat", side_effect=OSError):
            result = probe.capture(window, ancestry, 1)
        candidate = result["native_view_candidate"]
        self.assertFalse(candidate["snapshot_stable"])
        self.assertFalse(candidate["exists_regular_file"])

    def test_allocated_name_is_freed_if_decode_fails(self):
        probe = object.__new__(ShellViewProbe)
        freed = []
        probe._ole = NS(CoTaskMemFree=freed.append)
        def decode(pointer):
            raise ValueError("invalid string")
        probe._types = (NS(wstring_at=decode),)
        with self.assertRaises(ValueError):
            probe._path(NS(GetDisplayName=lambda form: 123))
        self.assertEqual(freed, [123])

    def test_session_mapping_label_is_not_formatted_as_an_event(self):
        self.assertIsNone(mapping_console_line({"type": "session", "mapping": "provisional_index_dry_run"}))
        event = {"sequence": 1, "mapping": {
            "status": "provisional", "candidate_index": 1,
            "candidate_path": "C:/fixture/a.txt", "rejection": "identity_correspondence_unproven",
        }}
        self.assertIn("candidate=C:/fixture/a.txt", mapping_console_line(event))

    def test_console_mapping_includes_failed_stage_and_hresult(self):
        event = {"sequence": 1, "mapping": {
            "status": "rejected", "candidate_index": 1, "candidate_path": None,
            "rejection": "native_probe_error",
        }, "shell_candidates": {"matching_windows": [{"active_view_association": {
            "stage": "query_service_provider", "hresult_hex": "0x80004002",
        }}]}}
        line = mapping_console_line(event)
        self.assertIn("stage=query_service_provider", line)
        self.assertIn("hresult=0x80004002", line)
