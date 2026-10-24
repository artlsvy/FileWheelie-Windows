"""Replay supplied tab evidence and adversarial variants; no Windows execution."""

import copy
import json
import unittest
from pathlib import Path

from filewheel.core.index_mapping import assess_index_mapping


FIXTURE = Path(__file__).parents[1] / "fixtures/windows_tabs_1_sanitized.json"


class TabMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.capture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def setUp(self):
        self.record = copy.deepcopy(self.capture["records"][0])

    def assess(self, record=None):
        record = self.record if record is None else record
        return assess_index_mapping(
            record, now=record["timestamp_monotonic"] + record["elapsed_ms"] / 1000,
        )

    def windows(self):
        return self.record["shell_candidates"]["matching_windows"]

    def assert_rejected(self, reason="ambiguous_shell_windows"):
        result = self.assess()
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["rejection"], reason)
        self.assertIsNone(result["candidate_path"])

    def test_captured_tabs_select_correct_unique_native_registration(self):
        expected = (
            (1, "C:\\fixture\\project\\tests\\a.txt"),
            (0, "C:\\fixture\\project\\README.md"),
            (1, "C:\\fixture\\project\\tests\\b.txt"),
            (0, "C:\\fixture\\project\\AGENTS.md"),
        )
        for record, (selected, path) in zip(self.capture["records"], expected, strict=True):
            with self.subTest(sequence=record["sequence"]):
                result = self.assess(record)
                self.assertEqual(result["status"], "provisional")
                self.assertEqual(result["candidate_path"], path)
                self.assertEqual(result["checks"]["shell_window_count"], 2)
                self.assertEqual(result["checks"]["selected_shell_window_index"], selected)
                self.assertTrue(result["checks"]["active_view_associated"])
                self.assertFalse(result["checks"]["identity_correspondence"])
                self.assertFalse(result["checks"]["filesystem_identity"])
                self.assertIsNone(record["resolved_path"])

    def test_registration_order_does_not_choose_target(self):
        self.windows().reverse()
        result = self.assess()
        self.assertEqual(result["candidate_path"], "C:\\fixture\\project\\tests\\a.txt")
        self.assertEqual(result["checks"]["selected_shell_window_index"], 0)

    def test_unknown_or_incomplete_peer_cannot_be_ignored(self):
        inactive = self.windows()[0]
        original = copy.deepcopy(inactive)
        for key in ("active_view_association", "item_count", "candidates", "truncated"):
            with self.subTest(key=key):
                inactive.clear()
                inactive.update(copy.deepcopy(original))
                del inactive[key]
                self.assert_rejected()

    def test_errored_peer_cannot_be_ignored(self):
        for update in (
            {"native_error": "unsupported_probe"},
            {"active_view_association": {"status": "unproven", "error_type": "COMError"}},
        ):
            with self.subTest(update=update):
                self.record = copy.deepcopy(self.capture["records"][0])
                self.windows()[0].update(update)
                self.assert_rejected()

    def test_duplicate_or_zero_matches_reject(self):
        original = copy.deepcopy(self.windows()[1])
        self.windows()[0] = copy.deepcopy(original)
        self.assert_rejected()
        self.windows()[0] = copy.deepcopy(self.capture["records"][0]["shell_candidates"]["matching_windows"][0])
        self.windows()[1] = copy.deepcopy(self.windows()[0])
        self.assert_rejected()

    def test_claimed_match_with_wrong_native_handles_rejects(self):
        for key in ("browser_hwnd", "view_hwnd", "items_view_hwnd", "tab_hwnd"):
            with self.subTest(key=key):
                self.record = copy.deepcopy(self.capture["records"][0])
                self.windows()[1]["active_view_association"][key] = 999
                self.assert_rejected()

    def test_partially_matching_peer_is_not_positive_exclusion(self):
        for key in ("browser_hwnd", "view_hwnd"):
            with self.subTest(key=key):
                self.record = copy.deepcopy(self.capture["records"][0])
                self.windows()[0]["active_view_association"][key] = (
                    self.windows()[1]["active_view_association"][key]
                )
                self.assert_rejected()

    def test_wrong_frame_or_missing_native_view_ancestry_rejects(self):
        self.windows()[0]["hwnd"] = 999
        self.assert_rejected()
        self.record = copy.deepcopy(self.capture["records"][0])
        self.record["uia_ancestry"] = [node for node in self.record["uia_ancestry"]
                                       if node["class_name"] != "DUIListView"]
        self.assert_rejected()

    def test_cross_tab_path_with_same_name_is_not_accepted(self):
        selected = self.windows()[1]
        selected["candidates"][1]["candidate_path"] = "C:\\other-tab\\a.txt"
        self.assert_rejected("native_candidate_mismatch")

    def test_truncation_in_any_registration_or_window_list_rejects(self):
        for position in (0, 1):
            with self.subTest(position=position):
                self.record = copy.deepcopy(self.capture["records"][0])
                self.windows()[position]["truncated"] = True
                self.assert_rejected()
        self.record = copy.deepcopy(self.capture["records"][0])
        self.record["shell_candidates"]["windows_truncated"] = True
        self.assert_rejected("truncated_shell_windows")

    def test_unstable_or_missing_selected_native_evidence_rejects(self):
        native = self.windows()[1].pop("native_view_candidate")
        self.assert_rejected("native_checks_incomplete")
        self.windows()[1]["native_view_candidate"] = native
        native["snapshot_stable"] = False
        self.assert_rejected("native_snapshot_changed")
        native["snapshot_stable"] = True
        self.record["snapshot_stable"] = False
        self.assert_rejected("snapshot_changed")

    def test_malformed_or_duplicate_peer_candidates_reject(self):
        self.windows()[0]["candidates"][0]["is_folder"] = "yes"
        self.assert_rejected()
        self.record = copy.deepcopy(self.capture["records"][0])
        self.windows()[0]["candidates"][0]["enumeration_index"] = 1
        self.assert_rejected()

    def test_selection_does_not_choose_registration_or_promote_identity(self):
        original = self.assess()
        self.record["uia_ancestry"][0]["selection_snapshot"]["is_selected"] = False
        self.record["selected_path"] = "C:\\wrong-tab\\selected.txt"
        for entry in self.windows():
            entry["active_tab_proven"] = True
            entry["active_view_association"]["windows_verified"] = True
        self.assertEqual(self.assess(), original)
