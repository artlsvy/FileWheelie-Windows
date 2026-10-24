"""A supplied native-success sample still must not cross the trust boundary."""

import json
import unittest
from pathlib import Path

from filewheel.core.index_mapping import assess_index_mapping


class StaCaptureReplayTests(unittest.TestCase):
    def setUp(self):
        fixture = Path(__file__).parents[1] / "fixtures/windows_sta_1_sanitized.json"
        self.capture = json.loads(fixture.read_text(encoding="utf-8"))
        self.record = self.capture["record"]

    def assess(self):
        return assess_index_mapping(
            self.record, now=self.record["timestamp_monotonic"] + self.record["elapsed_ms"] / 1000,
        )

    def test_native_success_with_unimplemented_position_is_only_provisional(self):
        result = self.assess()
        self.assertEqual(result["candidate_path"], "C:\\fixture\\project\\tests\\b.txt")
        self.assertEqual(result["status"], "provisional")
        self.assertEqual(result["rejection"], "identity_correspondence_unproven")
        for check in ("active_view_associated", "native_index_path_match", "native_regular_file",
                      "native_snapshot_stable"):
            self.assertTrue(result["checks"][check])
        self.assertFalse(result["checks"]["identity_correspondence"])
        native = self.record["shell_candidates"]["matching_windows"][0]["native_view_candidate"]
        self.assertEqual(native["position_error"]["hresult_name"], "E_NOTIMPL")
        self.assertIsNone(native["item_position_screen"])
        self.assertIsNone(self.record["resolved_path"])

    def test_selection_and_caller_verified_flags_cannot_promote_capture(self):
        original = self.assess()
        self.record["uia_ancestry"][0]["selection_snapshot"]["is_selected"] = False
        shell = self.record["shell_candidates"]["matching_windows"][0]
        shell["active_tab_proven"] = True
        shell["active_view_association"]["windows_verified"] = True
        self.assertEqual(self.assess(), original)
