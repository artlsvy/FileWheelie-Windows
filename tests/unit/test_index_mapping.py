"""Replay source is sanitized supplied evidence, not a Windows execution here."""

import copy
import json
import unittest
from pathlib import Path

from filewheel.core.index_mapping import assess_index_mapping


FIXTURE = Path(__file__).parents[1] / "fixtures/windows_run_2_sanitized.json"


class IndexMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.capture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def setUp(self):
        self.record = copy.deepcopy(self.capture["records"][0])

    def assess(self, record=None):
        record = self.record if record is None else record
        return assess_index_mapping(record, now=record["timestamp_monotonic"] + 0.1)

    def shell(self):
        return self.record["shell_candidates"]["matching_windows"][0]

    def item(self):
        return next(node for node in self.record["uia_ancestry"]
                    if node["class_name"] == "UIItem")

    def candidate(self):
        index = int(self.item()["automation_id"])
        return next(item for item in self.shell()["candidates"]
                    if item["enumeration_index"] == index)

    def test_all_supplied_file_hits_are_provisional_and_chrome_rejected(self):
        results = [self.assess(record) for record in self.capture["records"]]
        self.assertEqual(sum(result["status"] == "provisional" for result in results), 9)
        self.assertEqual(sum(result["rejection"] == "non_file_element" for result in results), 2)
        self.assertEqual(self.capture["summary"]["worker_received"], 14)
        self.assertEqual(self.capture["summary"]["counts"]["non_explorer_process"], 3)
        self.assertEqual([result["candidate_index"] for result in results[-3:]], [11, 9, 10])
        for result in results:
            self.assertFalse(result["checks"]["identity_correspondence"])
            self.assertNotEqual(result["status"], "verified")

    def test_index_candidate_comes_from_shell_not_selection(self):
        result = self.assess()
        self.assertEqual(result["candidate_index"], 2)
        self.assertEqual(result["candidate_path"], "C:\\fixture\\project\\tests\\b.txt")
        self.assertEqual(result["rejection"], "active_view_unproven")
        self.item()["selection_snapshot"] = {"is_selected": False, "status": "observed"}
        self.record["selected_path"] = "C:\\wrong\\selected.txt"
        self.assertEqual(self.assess(), result)

    def test_mismatched_index_does_not_substitute_name_match(self):
        self.item()["automation_id"] = "1"
        self.assertEqual(self.assess()["rejection"], "inconsistent_names")
        self.assertIsNone(self.assess()["candidate_path"])

    def test_invalid_and_out_of_range_indices(self):
        for index in ("-1", "02", "+2", "2.0", "", "٢", "9", 2):
            with self.subTest(index=index):
                self.item()["automation_id"] = index
                result = self.assess()
                self.assertEqual(result["status"], "rejected")
                self.assertIsNone(result["candidate_path"])

    def test_invalid_geometry_ignores_forged_contains_point_flag(self):
        for bounds in ([0, 0, 0, 0], [2000, 2000, 2001, 2001],
                       [float("nan"), 0, 20, 20], [0, 0, 1], None):
            with self.subTest(bounds=bounds):
                self.item()["bounds"] = bounds
                self.item()["contains_point"] = True
                result = self.assess()
                self.assertEqual(result["rejection"], "invalid_geometry")
                json.dumps(result, allow_nan=False)

    def test_wrong_process_or_missing_view_ancestry_rejects(self):
        self.item()["process_id"] = 99
        self.assertEqual(self.assess()["rejection"], "uia_process_mismatch")
        self.item()["process_id"] = self.record["window"]["pid"]
        del self.record["uia_ancestry"][1]
        self.assertEqual(self.assess()["rejection"], "invalid_view_ancestry")

    def test_multiple_shell_tabs_and_ambiguous_association_reject(self):
        self.shell()["active_view_association"] = {"status": "ambiguous"}
        self.assertEqual(self.assess()["rejection"], "ambiguous_active_view")
        self.shell().pop("active_view_association")
        self.record["shell_candidates"]["matching_windows"].append(copy.deepcopy(self.shell()))
        self.assertEqual(self.assess()["rejection"], "ambiguous_shell_windows")

    def test_active_view_evidence_must_match_captured_handles(self):
        self.shell()["active_view_association"] = {
            "status": "matched", "view_hwnd": 2297952, "tab_hwnd": 18679786,
            "items_view_hwnd": 999, "browser_hwnd": 18679786,
        }
        self.assertEqual(self.assess()["rejection"], "active_view_mismatch")
        self.shell()["active_view_association"]["items_view_hwnd"] = 6097010
        result = self.assess()
        self.assertTrue(result["checks"]["active_view_associated"])
        self.assertEqual(result["status"], "provisional")
        self.assertEqual(result["rejection"], "identity_correspondence_unproven")
        self.assertFalse(result["checks"]["identity_correspondence"])

    def test_truncated_and_duplicate_candidate_indices_reject(self):
        self.shell()["truncated"] = True
        self.assertEqual(self.assess()["rejection"], "truncated_candidates")
        self.shell()["truncated"] = False
        self.candidate()["enumeration_index"] = 1
        self.assertEqual(self.assess()["rejection"], "inconsistent_candidate_indices")

    def test_folder_and_virtual_objects_reject(self):
        candidate = self.candidate()
        candidate["is_folder"] = True
        self.assertEqual(self.assess()["rejection"], "unsupported_shell_object")
        candidate["is_folder"] = False
        candidate["is_filesystem"] = False
        self.assertEqual(self.assess()["rejection"], "unsupported_shell_object")

    def test_local_unicode_candidate_is_provisional(self):
        self.item()["name"] = "資料 æøå.txt"
        self.candidate()["candidate_path"] = "C:\\fixture\\資料 æøå.txt"
        self.assertEqual(self.assess()["status"], "provisional")

    def test_unsafe_paths_reject(self):
        candidate = self.candidate()
        for path in ("b.txt", "C:b.txt", "\\\\server\\share\\b.txt", "\\\\?\\C:\\b.txt",
                     "C:\\test\\b.txt:secret", "C:\\test\\..\\b.txt", "C:\\NUL.txt"):
            with self.subTest(path=path):
                candidate["candidate_path"] = path
                self.assertEqual(self.assess()["rejection"], "unsupported_candidate_path")

    def test_hidden_extension_remains_unknown(self):
        self.item()["name"] = "b"
        result = self.assess()
        self.assertEqual(result["status"], "provisional")
        self.assertIsNone(result["checks"]["name_corroboration"])

    def test_duplicate_display_stems_reject(self):
        self.item()["name"] = "same"
        self.shell()["candidates"][1]["candidate_path"] = "C:\\fixture\\same.docx"
        self.candidate()["candidate_path"] = "C:\\fixture\\same.pdf"
        self.assertEqual(self.assess()["rejection"], "ambiguous_display_name")

    def test_conflicting_shell_display_name_rejects(self):
        self.candidate()["display_name"] = "other.txt"
        self.assertEqual(self.assess()["rejection"], "inconsistent_names")

    def test_stale_future_and_nonfinite_times_reject(self):
        timestamp = self.record["timestamp_monotonic"]
        for now in (timestamp + 0.501, timestamp - 1, float("inf"), float("nan")):
            with self.subTest(now=now):
                self.assertEqual(assess_index_mapping(self.record, now=now)["status"], "rejected")

    def test_changed_or_error_snapshots_reject(self):
        for key, value, reason in (("snapshot_stable", False, "snapshot_changed"),
                                   ("uia_recheck_unchanged", False, "uia_changed"),
                                   ("rejection", "evidence_error", "evidence_error")):
            with self.subTest(key=key):
                changed = copy.deepcopy(self.record)
                changed[key] = value
                self.assertEqual(self.assess(changed)["rejection"], reason)

    def test_malformed_records_fail_closed(self):
        for malformed in (None, [], {}, {"schema_version": 1, "point": [1, 2]},
                          {**self.record, "point": [True, 1]},
                          {**self.record, "injected": True}):
            with self.subTest(malformed=malformed):
                result = assess_index_mapping(malformed, now=1)
                self.assertEqual(result["status"], "rejected")
                self.assertIsNone(result["candidate_path"])

    def native_candidate(self):
        return {
            "index": 2, "candidate_path": self.candidate()["candidate_path"],
            "is_filesystem": True, "is_folder": False, "exists_regular_file": True,
            "is_reparse_point": False, "snapshot_stable": True,
            "local_fixed_drive": True,
        }

    def test_independent_native_candidate_corroborates_but_cannot_verify(self):
        self.shell()["native_view_candidate"] = self.native_candidate()
        result = self.assess()
        self.assertEqual(result["status"], "provisional")
        self.assertTrue(result["checks"]["native_index_path_match"])
        self.assertTrue(result["checks"]["native_regular_file"])
        self.assertFalse(result["checks"]["identity_correspondence"])

    def test_native_conflicts_reject(self):
        for update, reason in (
            ({"index": 1}, "native_candidate_mismatch"),
            ({"candidate_path": "C:\\wrong.txt"}, "native_candidate_mismatch"),
            ({"exists_regular_file": False}, "native_file_missing_or_not_regular"),
            ({"is_filesystem": False}, "unsupported_native_object"),
            ({"is_reparse_point": True}, "native_reparse_point"),
            ({"snapshot_stable": False}, "native_snapshot_changed"),
            ({"local_fixed_drive": False}, "unsupported_native_drive"),
        ):
            with self.subTest(update=update):
                self.shell()["native_view_candidate"] = {**self.native_candidate(), **update}
                self.assertEqual(self.assess()["rejection"], reason)

    def test_native_probe_failure_is_not_hidden_by_consistent_candidate(self):
        self.shell()["native_view_candidate"] = self.native_candidate()
        for error, reason in (("view_index_or_size", "native_view_index_or_size"),
                              ("unsupported_probe", "native_probe_error")):
            with self.subTest(error=error):
                self.shell()["native_error"] = error
                result = self.assess()
                self.assertEqual(result["status"], "rejected")
                self.assertEqual(result["rejection"], reason)
                self.assertIsNone(result["candidate_path"])

    def test_native_association_error_rejects_even_when_status_is_matched(self):
        self.shell()["active_view_association"] = {
            "status": "matched", "view_hwnd": 2297952, "tab_hwnd": 18679786,
            "items_view_hwnd": 6097010, "browser_hwnd": 18679786,
            "error_type": "COMError",
        }
        self.assertEqual(self.assess()["rejection"], "native_probe_error")

    def test_unknown_native_validation_checks_are_explicitly_incomplete(self):
        for missing in ("exists_regular_file", "snapshot_stable", "is_reparse_point",
                        "local_fixed_drive"):
            with self.subTest(missing=missing):
                native = self.native_candidate()
                del native[missing]
                self.shell()["native_view_candidate"] = native
                result = self.assess()
                self.assertEqual(result["status"], "rejected")
                self.assertEqual(result["rejection"], "native_checks_incomplete")
