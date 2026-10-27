import unittest

from filewheel.core.models import MouseEvent
from filewheel.platforms.windows.explorer_resolver import proven_target_from_evidence


class PlatformSeamTests(unittest.TestCase):
    def test_unproven_mapping_never_uses_name_or_selection(self):
        for evidence in (
            {}, {"selected_path": "C:/wrong.txt"},
            {"name": "report", "candidate_path": "C:/report.docx"},
            {"candidates": ["C:/report.docx", "C:/report.pdf"]},
        ):
            with self.subTest(evidence=evidence):
                self.assertIsNone(proven_target_from_evidence(MouseEvent(1, (0, 0), 1, 123), evidence))
