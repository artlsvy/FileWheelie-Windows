import ctypes
import io
import json
import unittest
from threading import Event
from types import SimpleNamespace

from filewheel.core.controller import InvocationController
from filewheel.core.models import MouseEvent
from filewheel.platforms.windows.diagnostics import write_record
from filewheel.platforms.windows.explorer_resolver import ExplorerTargetResolver


class GeneratedPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def fake_resolver(element):
    resolver = object.__new__(ExplorerTargetResolver)
    resolver._point_type = GeneratedPoint

    def element_from_point(point):
        if not isinstance(point, GeneratedPoint):
            raise TypeError("generated UIA point required")
        return element

    resolver._automation = SimpleNamespace(
        ElementFromPoint=element_from_point, RawViewWalker=object()
    )
    return resolver


class DiagnosticSafetyTests(unittest.TestCase):
    def test_generated_point_type_is_used(self):
        element = SimpleNamespace(
            CurrentProcessId=7, CurrentName="A", CurrentAutomationId="item",
            CurrentClassName="UIItem", CurrentControlType=50029,
            CurrentNativeWindowHandle=123, GetRuntimeId=lambda: [1, 2],
            CurrentBoundingRectangle=SimpleNamespace(left=-5, top=0, right=5, bottom=10),
        )
        records = fake_resolver(element)._uia_evidence(MouseEvent(1, (0, 2), 1, 123), 7)
        self.assertTrue(records[0]["contains_point"])

    def test_foreign_uia_process_is_rejected_before_text_access(self):
        class ForeignElement:
            CurrentProcessId = 99

            @property
            def CurrentName(self):
                raise AssertionError("foreign text read")

        with self.assertRaisesRegex(ValueError, "process changed"):
            fake_resolver(ForeignElement())._uia_evidence(MouseEvent(1, (0, 2), 1, 123), 7)

    def test_window_change_discards_payload(self):
        resolver = object.__new__(ExplorerTargetResolver)
        window = {
            "process_image": "C:/Windows/explorer.exe", "class_name": "CabinetWClass",
            "root_hwnd": 123, "foreground_hwnd": 123, "pid": 7,
        }
        snapshots = iter([window, {**window, "foreground_hwnd": 555}])
        resolver._native = SimpleNamespace(window_evidence=lambda point: next(snapshots))
        resolver._uia_evidence = lambda event, pid: [{"name": "private"}]
        resolver._shell_evidence = lambda hwnd: {"candidate_path": "C:/private.txt"}
        records = []
        resolver._write = records.append
        from time import monotonic
        self.assertIsNone(resolver.resolve(MouseEvent(1, (0, 2), monotonic(), 123)))
        self.assertEqual(records[0]["rejection"], "window_changed")
        self.assertNotIn("uia_ancestry", records[0])
        self.assertNotIn("shell_candidates", records[0])

    def test_write_failure_remains_visible_across_controller_boundary(self):
        class BrokenStream:
            def write(self, text):
                raise OSError("disk full")

        failed = Event()

        class Resolver:
            def resolve(self, event):
                write_record(BrokenStream(), {"resolved_path": None}, failed)

        controller = InvocationController(Resolver())
        self.assertIsNone(controller.handle(MouseEvent(1, (0, 2), 1, 123)))
        self.assertTrue(failed.is_set())

    def test_unicode_jsonl_round_trip(self):
        stream = io.StringIO()
        failed = Event()
        record = {"candidate_path": "C:/files/æøå.txt", "resolved_path": None}
        write_record(stream, record, failed)
        self.assertEqual(json.loads(stream.getvalue()), record)
        self.assertFalse(failed.is_set())
