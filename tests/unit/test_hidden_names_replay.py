"""Actual hidden UIA labels and Unicode path, with three Shell registrations."""

import json
import unittest
from pathlib import Path

from filewheel.core.index_mapping import assess_index_mapping


class HiddenNamesReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).parents[1] / "fixtures/windows_names_2_sanitized.json"
        cls.capture = json.loads(path.read_text(encoding="utf-8"))

    def assess(self, record):
        return assess_index_mapping(
            record, now=record["timestamp_monotonic"] + record["elapsed_ms"] / 1000,
        )

    def test_nonascii_hidden_stem_keeps_shell_extension_and_codepoints(self):
        record = self.capture["records"][0]
        result = self.assess(record)
        self.assertEqual(record["uia_ancestry"][0]["name"], "unicode-æøå")
        self.assertEqual(result["candidate_path"], "C:\\fixture\\names\\unicode-æøå.txt")
        self.assertEqual(result["status"], "provisional")
        self.assertEqual(result["checks"]["shell_window_count"], 3)
        self.assertEqual(result["checks"]["selected_shell_window_index"], 0)
        self.assertIsNone(result["checks"]["name_corroboration"])
        self.assertFalse(result["checks"]["identity_correspondence"])

    def test_duplicate_hidden_labels_reject_despite_available_native_paths(self):
        for record in self.capture["records"][1:]:
            with self.subTest(sequence=record["sequence"]):
                self.assertEqual(record["uia_ancestry"][0]["name"], "report")
                native = record["shell_candidates"]["matching_windows"][0]["native_view_candidate"]
                self.assertTrue(native["snapshot_stable"])
                self.assertTrue(native["exists_regular_file"])
                result = self.assess(record)
                self.assertEqual(result["status"], "rejected")
                self.assertEqual(result["rejection"], "ambiguous_display_name")
                self.assertIsNone(result["candidate_path"])
                self.assertIsNone(record["resolved_path"])
