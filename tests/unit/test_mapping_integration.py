"""Portable tests for diagnostic wiring; native collection is replaced by replay."""

import copy
import json
import unittest
from collections import Counter
from pathlib import Path
from time import monotonic
from types import SimpleNamespace

from filewheel.core.models import MouseEvent
from filewheel.platforms.windows.explorer_resolver import ExplorerTargetResolver


class MappingIntegrationTests(unittest.TestCase):
    def test_dry_run_reports_candidate_and_never_returns_trusted_resolution(self):
        records, result = self.run_replay(window_changed=False)
        self.assertIsNone(result)
        self.assertIsNone(records[0]["resolved_path"])
        self.assertEqual(records[0]["mapping"]["status"], "provisional")
        self.assertTrue(records[0]["snapshot_stable"])
        self.assertEqual(records[0]["mapping"]["candidate_index"], 2)

    def test_window_race_discards_candidate_report_as_well_as_raw_payload(self):
        records, result = self.run_replay(window_changed=True)
        self.assertIsNone(result)
        self.assertEqual(records[0]["rejection"], "window_changed")
        for key in ("mapping", "shell_candidates", "uia_ancestry"):
            self.assertNotIn(key, records[0])

    def run_replay(self, window_changed):
        fixture = Path(__file__).parents[1] / "fixtures/windows_run_2_sanitized.json"
        record = json.loads(fixture.read_text(encoding="utf-8"))["records"][0]
        resolver = object.__new__(ExplorerTargetResolver)
        resolver._dry_run_mapping = True
        resolver.counts = Counter()
        first = record["window"]
        second = {**first, "foreground_hwnd": 555} if window_changed else first
        snapshots = iter([first, second])
        resolver._native = SimpleNamespace(window_evidence=lambda point: next(snapshots))
        resolver._uia_evidence = lambda event, pid: copy.deepcopy(record["uia_ancestry"])
        resolver._shell_evidence = lambda hwnd, ancestry: copy.deepcopy(record["shell_candidates"])
        written = []
        resolver._write = written.append
        result = resolver.resolve(MouseEvent(
            record["sequence"], tuple(record["point"]), monotonic(), first["foreground_hwnd"],
        ))
        return written, result
