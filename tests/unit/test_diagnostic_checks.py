import unittest
from collections import Counter
from time import monotonic
from types import SimpleNamespace

from filewheel.core.diagnostic_checks import explorer_rejection
from filewheel.core.models import MouseEvent
from filewheel.platforms.windows.explorer_resolver import ExplorerTargetResolver


class DiagnosticChecksTests(unittest.TestCase):
    def setUp(self):
        self.event = MouseEvent(1, (20, 30), monotonic(), 123)
        self.window = {
            "process_image": "C:/Windows/explorer.exe", "class_name": "CabinetWClass",
            "root_hwnd": 123, "foreground_hwnd": 123, "pid": 7,
        }

    def test_provenance_cases(self):
        self.assertIsNone(explorer_rejection(self.event, self.window))
        for update, reason in (
            ({"process_image": "C:/other/editor.exe"}, "non_explorer_process"),
            ({"process_image": None}, "process_unavailable"),
            ({"class_name": "Progman"}, "unsupported_explorer_surface"),
            ({"foreground_hwnd": 555}, "window_mismatch"),
            ({"root_hwnd": 555}, "window_mismatch"),
        ):
            with self.subTest(update=update):
                self.assertEqual(explorer_rejection(self.event, {**self.window, **update}), reason)

    def test_non_explorer_is_counted_without_uia_shell_or_payload(self):
        resolver = object.__new__(ExplorerTargetResolver)
        resolver.counts = Counter()
        resolver._native = SimpleNamespace(window_evidence=lambda point: {
            **self.window, "process_image": "C:/other/editor.exe",
        })
        resolver._write = lambda record: self.fail("unrelated payload written")
        # No automation or Shell objects: touching either would raise.
        self.assertIsNone(resolver.resolve(self.event))
        self.assertEqual(resolver.counts, {"resolver_calls": 1, "non_explorer_process": 1})

    def test_selection_snapshot_observes_true_and_false_without_mutation(self):
        resolver = object.__new__(ExplorerTargetResolver)
        resolver._selection_type = object()
        for selected in (False, True):
            class Pattern:
                def QueryInterface(inner, interface):
                    self.assertIs(interface, resolver._selection_type)
                    return SimpleNamespace(CurrentIsSelected=selected)

            def get_pattern(pattern_id):
                self.assertEqual(pattern_id, 10010)
                return Pattern()

            element = SimpleNamespace(GetCurrentPattern=get_pattern)
            self.assertEqual(resolver._selection_evidence(element), {
                "is_selected": selected, "status": "observed",
            })

    def test_missing_selection_pattern_is_unknown_never_false(self):
        resolver = object.__new__(ExplorerTargetResolver)
        self.assertEqual(resolver._selection_evidence(object()), {
            "is_selected": None, "status": "unavailable_or_error",
        })
        element = SimpleNamespace(GetCurrentPattern=lambda pattern_id: None)
        self.assertEqual(resolver._selection_evidence(element), {
            "is_selected": None, "status": "unavailable",
        })
