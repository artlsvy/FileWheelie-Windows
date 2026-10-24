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

    def bounded_candidates(self, count=51):
        return [
            {
                "enumeration_index": index,
                "candidate_path": f"C:\\fixture\\inactive\\item-{index}.txt",
                "is_folder": False, "is_filesystem": True,
            }
            for index in range(min(count, 32))
        ]

    def set_bounded_inactive(self):
        inactive = self.windows()[0]
        inactive.update(item_count=51, truncated=True, candidates=self.bounded_candidates())
        return inactive

    def test_bounded_listing_of_positively_excluded_inactive_tab_is_allowed(self):
        self.set_bounded_inactive()
        result = self.assess()
        self.assertEqual(result["status"], "provisional")
        self.assertEqual(result["candidate_path"], "C:\\fixture\\project\\tests\\a.txt")
        self.assertEqual(result["checks"]["selected_shell_window_index"], 1)
        self.assertFalse(result["checks"]["identity_correspondence"])
        self.windows().reverse()
        self.assertEqual(self.assess()["candidate_path"], result["candidate_path"])

    def test_control_class_capture_replays_with_large_inactive_tab(self):
        fixture = FIXTURE.with_name("windows_control_class_1_sanitized.json")
        record = json.loads(fixture.read_text(encoding="utf-8"))["record"]
        self.assertEqual(record["rejection"], "ambiguous_shell_windows")
        self.assertTrue(record["shell_candidates"]["matching_windows"][1]["truncated"])
        result = self.assess(record)
        self.assertEqual(result["status"], "provisional")
        self.assertEqual(result["candidate_path"], "C:\\fixture\\project\\tests\\a.txt")
        self.assertEqual(result["checks"]["shell_window_count"], 3)
        self.assertEqual(result["checks"]["selected_shell_window_index"], 2)
        self.assertFalse(result["checks"]["identity_correspondence"])
        self.assertIsNone(record["resolved_path"])

    def test_bounded_listing_of_matched_tab_still_rejects(self):
        self.windows()[1].update(item_count=51, truncated=True, candidates=self.bounded_candidates())
        self.assert_rejected()

    def test_inactive_prefix_does_not_relax_global_registration_truncation(self):
        self.set_bounded_inactive()
        self.record["shell_candidates"]["windows_truncated"] = True
        self.assert_rejected("truncated_shell_windows")

    def test_inactive_prefix_requires_consistent_count_length_and_flags(self):
        for update in (
            {"item_count": None}, {"item_count": True}, {"item_count": -1},
            {"item_count": 31}, {"item_count": 32},
            {"truncated": False}, {"truncated": "true"},
            {"candidates": self.bounded_candidates()[:-1]},
            {"candidates": self.bounded_candidates() + [self.bounded_candidates()[0]]},
        ):
            with self.subTest(update=update):
                self.record = copy.deepcopy(self.capture["records"][0])
                self.set_bounded_inactive().update(update)
                self.assert_rejected()

    def test_inactive_prefix_candidate_metadata_and_indices_still_validate(self):
        for update in (
            {"enumeration_index": 32}, {"enumeration_index": True},
            {"candidate_path": None}, {"candidate_path": ""},
            {"candidate_path": "x" * 2049}, {"is_folder": "false"},
            {"is_filesystem": None},
        ):
            with self.subTest(update=update):
                self.record = copy.deepcopy(self.capture["records"][0])
                inactive = self.set_bounded_inactive()
                inactive["candidates"][0].update(update)
                self.assert_rejected()
        self.record = copy.deepcopy(self.capture["records"][0])
        inactive = self.set_bounded_inactive()
        inactive["candidates"][0]["enumeration_index"] = 1
        self.assert_rejected()

    def test_bounded_inactive_listing_cannot_substitute_for_hwnd_exclusion(self):
        for update in (
            {"error_type": "COMError"}, {"status": "matched"},
            {"browser_hwnd": 0}, {"view_hwnd": 0},
            {"browser_hwnd": 2361942}, {"view_hwnd": 527006},
        ):
            with self.subTest(update=update):
                self.record = copy.deepcopy(self.capture["records"][0])
                self.set_bounded_inactive()["active_view_association"].update(update)
                self.assert_rejected()

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
