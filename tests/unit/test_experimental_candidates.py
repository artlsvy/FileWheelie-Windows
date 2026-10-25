"""Untrusted replay candidates cannot route without fresh, explicit user choice."""

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import Mock

from filewheel.core.controller import InvocationController
from filewheel.core.experimental import CandidateGate, ExperimentalCandidate, candidate_from_record
from filewheel.core.explicit_paths import FileCheck
from filewheel.core.models import TargetResolution


def captured_record():
    fixture = Path(__file__).parents[1] / "fixtures/windows_sta_1_sanitized.json"
    return json.loads(fixture.read_text(encoding="utf-8"))["record"]


class ExperimentalCandidateTests(unittest.TestCase):
    def setUp(self):
        self.record = captured_record()
        self.now = self.record["timestamp_monotonic"] + 0.12

    def candidate(self):
        return candidate_from_record(self.record, now=self.now)

    def test_native_fixture_is_distinct_untrusted_dto_with_unique_token(self):
        first, second = self.candidate(), self.candidate()
        self.assertIsInstance(first, ExperimentalCandidate)
        self.assertNotIsInstance(first, TargetResolution)
        self.assertEqual(str(first.path), r"C:\fixture\project\tests\b.txt")
        self.assertEqual(first.point, tuple(self.record["point"]))
        self.assertNotEqual(first.token, second.token)
        self.assertIsNone(self.record["resolved_path"])

    def test_supplied_mapping_flags_do_not_replace_assessed_path(self):
        self.record["mapping"] = {
            "status": "provisional",
            "candidate_path": r"C:\wrong.txt",
            "checks": {"identity_correspondence": True},
        }
        self.assertEqual(str(self.candidate().path), r"C:\fixture\project\tests\b.txt")

    def test_native_path_conflict_missing_fields_and_nonlocal_reject(self):
        native = self.record["shell_candidates"]["matching_windows"][0]["native_view_candidate"]
        for key, invalid in (
            ("candidate_path", r"C:\wrong.txt"),
            ("snapshot_stable", False),
            ("exists_regular_file", False),
            ("is_reparse_point", True),
            ("local_fixed_drive", False),
            ("local_fixed_drive", None),
        ):
            with self.subTest(key=key, invalid=invalid):
                original = native[key]
                native[key] = invalid
                self.assertIsNone(self.candidate())
                native[key] = original

    def test_stale_snapshot_nonexplorer_injected_and_ambiguous_tabs_reject(self):
        self.assertIsNone(candidate_from_record(self.record, now=self.now + 0.6))
        for key, value in (("injected", True), ("snapshot_stable", False)):
            modified = copy.deepcopy(self.record)
            modified[key] = value
            self.assertIsNone(candidate_from_record(modified, now=self.now))
        modified = copy.deepcopy(self.record)
        modified["window"]["process_image"] = r"C:\not-explorer.exe"
        self.assertIsNone(candidate_from_record(modified, now=self.now))
        modified = copy.deepcopy(self.record)
        windows = modified["shell_candidates"]["matching_windows"]
        windows.append(copy.deepcopy(windows[0]))
        self.assertIsNone(candidate_from_record(modified, now=self.now))

    def test_no_native_evidence_or_ambiguous_hidden_name_never_offered(self):
        modified = copy.deepcopy(self.record)
        del modified["shell_candidates"]["matching_windows"][0]["native_view_candidate"]
        self.assertIsNone(candidate_from_record(modified, now=self.now))
        modified = copy.deepcopy(self.record)
        modified["uia_ancestry"][0]["name"] = "b"
        window = modified["shell_candidates"]["matching_windows"][0]
        other = copy.deepcopy(window["candidates"][-1])
        other["candidate_path"] = r"C:\fixture\project\tests\b.pdf"
        other["enumeration_index"] = 4
        window["candidates"].append(other)
        window["item_count"] = 5
        self.assertIsNone(candidate_from_record(modified, now=self.now))

    def test_confirmation_is_explicit_revalidated_one_shot_and_its_own_source(self):
        gate = CandidateGate()
        candidate = gate.offer(self.candidate())
        inspector = Mock(return_value=FileCheck(True, True))
        inspector.assert_not_called()
        result = gate.confirm(candidate.token, InvocationController(), inspector, now=self.now + 1)
        self.assertEqual(result.target.path, candidate.path)
        self.assertEqual(result.target.point, candidate.point)
        self.assertEqual(result.target.source, "user_confirmed_candidate")
        inspector.assert_called_once_with(candidate.path)
        replay = gate.confirm(candidate.token, InvocationController(), inspector, now=self.now + 2)
        self.assertIsNone(replay.target)
        self.assertEqual(replay.rejection, "candidate_not_current")
        inspector.assert_called_once()

    def test_expired_cancelled_and_superseded_tokens_cannot_confirm(self):
        gate = CandidateGate()
        inspector = Mock(return_value=FileCheck(True, True))
        first = gate.offer(self.candidate())
        self.assertEqual(
            gate.confirm(
                first.token, InvocationController(), inspector, now=self.now + 30.01
            ).rejection,
            "candidate_expired",
        )
        first = gate.offer(self.candidate())
        second = gate.offer(self.candidate())
        self.assertEqual(
            gate.confirm(
                first.token, InvocationController(), inspector, now=self.now + 1
            ).rejection,
            "candidate_not_current",
        )
        gate.cancel()
        self.assertIsNone(
            gate.confirm(second.token, InvocationController(), inspector, now=self.now + 1).target
        )
        inspector.assert_not_called()

    def test_disappeared_file_and_cancel_during_inspection_do_not_route(self):
        gate = CandidateGate()
        candidate = gate.offer(self.candidate())
        missing = gate.confirm(
            candidate.token,
            InvocationController(),
            lambda path: FileCheck(False, False),
            now=self.now + 1,
        )
        self.assertEqual(missing.rejection, "missing_file")
        candidate = gate.offer(self.candidate())

        def cancelled_inspection(path):
            gate.cancel()
            return FileCheck(True, True)

        self.assertEqual(
            gate.confirm(
                candidate.token, InvocationController(), cancelled_inspection, now=self.now + 1
            ).rejection,
            "candidate_superseded",
        )

    def test_is_current_checks_ttl_and_supersession_without_consuming(self):
        gate = CandidateGate()
        first = gate.offer(self.candidate())
        self.assertTrue(gate.is_current(first.token, now=self.now + 1))
        self.assertTrue(gate.is_current(first.token, now=self.now + 2))
        self.assertFalse(gate.is_current(first.token, now=self.now + 31))
        self.assertFalse(gate.is_current(first.token, now=self.now - 1))
        second = gate.offer(self.candidate())
        self.assertFalse(gate.is_current(first.token, now=self.now + 1))
        self.assertTrue(gate.is_current(second.token, now=self.now + 1))
        gate.cancel()
        self.assertFalse(gate.is_current(second.token, now=self.now + 1))

    def test_missing_uia_stability_snapshot_is_not_enough_for_ui_offer(self):
        del self.record["snapshot_stable"]
        self.assertIsNone(self.candidate())
