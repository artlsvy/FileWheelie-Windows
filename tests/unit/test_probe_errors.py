import json
import unittest

from filewheel.core.probe_errors import ProbeFailure, probe_step


class FakeCOMError(Exception):
    def __init__(self, code, message="private C:/secret/name.txt"):
        super().__init__(code, message, {"description": message})
        self.hresult = code


def fail(error):
    raise error


class ProbeErrorTests(unittest.TestCase):
    def evidence(self, error, stages=None):
        with self.assertRaises(ProbeFailure) as failure:
            probe_step([] if stages is None else stages, "QueryService", fail, error)
        return failure.exception.evidence

    def test_success_returns_value_and_appends_stage(self):
        stages = ["QueryInterface"]
        self.assertEqual(probe_step(stages, "GetWindow", lambda x: x + 1, 40), 41)
        self.assertEqual(stages, ["QueryInterface", "GetWindow"])

    def test_known_hresult_signed_and_unsigned_are_equivalent(self):
        for unsigned, name in (
            (0x80004001, "E_NOTIMPL"), (0x80004002, "E_NOINTERFACE"),
            (0x80004005, "E_FAIL"), (0x80070005, "E_ACCESSDENIED"),
            (0x8001010E, "RPC_E_WRONG_THREAD"), (0x800401F0, "CO_E_NOTINITIALIZED"),
            (0x80020003, "DISP_E_MEMBERNOTFOUND"),
        ):
            with self.subTest(name=name):
                signed = unsigned - 2**32
                first = self.evidence(FakeCOMError(unsigned))
                self.assertEqual(first, self.evidence(FakeCOMError(signed)))
                self.assertEqual(first["hresult"], signed)
                self.assertEqual(first["hresult_hex"], f"0x{unsigned:08X}")
                self.assertEqual(first["hresult_name"], name)

    def test_attribute_is_preferred_to_first_argument(self):
        error = FakeCOMError(0x80004002)
        error.args = (0x80004005, "private text")
        self.assertEqual(self.evidence(error)["hresult_name"], "E_NOINTERFACE")

    def test_exact_integer_first_argument_is_supported(self):
        evidence = self.evidence(Exception(0x80004005, "private text"))
        self.assertEqual(evidence["hresult_name"], "E_FAIL")

    def test_no_exception_message_errorinfo_or_traceback_is_copied(self):
        evidence = self.evidence(FakeCOMError(0x80004005))
        encoded = json.dumps(evidence)
        for private in ("private", "secret", "name.txt", "description", "traceback"):
            self.assertNotIn(private, encoded)
        self.assertEqual(set(evidence), {
            "stage", "error_type", "hresult", "hresult_hex", "hresult_name", "completed_stages",
        })

    def test_malformed_hresult_values_are_not_coerced(self):
        for value in (True, False, "0x80004005", None, 1.0, -(2**31) - 1, 2**32):
            with self.subTest(value=value):
                evidence = self.evidence(FakeCOMError(value))
                self.assertIsNone(evidence["hresult"])
                self.assertIsNone(evidence["hresult_hex"])
                self.assertIsNone(evidence["hresult_name"])

    def test_failing_hresult_property_can_fall_back_to_numeric_argument(self):
        class BadProperty(Exception):
            @property
            def hresult(self):
                raise RuntimeError("private property text")

        evidence = self.evidence(BadProperty(0x80004005, "private text"))
        self.assertEqual(evidence["hresult_name"], "E_FAIL")

    def test_unknown_valid_hresult_keeps_only_numeric_code(self):
        evidence = self.evidence(FakeCOMError(0x81234567))
        self.assertEqual(evidence["hresult_hex"], "0x81234567")
        self.assertIsNone(evidence["hresult_name"])

    def test_nested_probe_failure_keeps_original_evidence(self):
        original = ProbeFailure({"stage": "Inner"})
        stages = ["Before"]
        with self.assertRaises(ProbeFailure) as failure:
            probe_step(stages, "Outer", fail, original)
        self.assertIs(failure.exception, original)
        self.assertEqual(stages, ["Before"])

    def test_completed_stages_are_copied_and_bounded(self):
        stages = [f"stage-{index}" for index in range(40)]
        stages[-1] = "x" * 200
        evidence = self.evidence(Exception("private text"), stages)
        self.assertEqual(len(evidence["completed_stages"]), 32)
        self.assertEqual(len(evidence["completed_stages"][-1]), 160)
        stages.clear()
        self.assertEqual(len(evidence["completed_stages"]), 32)

    def test_successful_stage_history_and_labels_are_bounded(self):
        stages = ["before"] * 40
        probe_step(stages, "x" * 200, lambda: None)
        self.assertEqual(len(stages), 32)
        self.assertEqual(stages[-1], "x" * 160)
        with self.assertRaises(ProbeFailure) as failure:
            probe_step(stages, "y" * 200, fail, Exception())
        self.assertEqual(len(failure.exception.evidence["stage"]), 160)
