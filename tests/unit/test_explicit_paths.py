"""Portable validation and shared-controller routing; no Windows runtime proof."""

import unittest
from pathlib import PureWindowsPath

from filewheel.core.controller import InvocationController
from filewheel.core.explicit_paths import FileCheck, validate_explicit_paths
from filewheel.core.models import MouseEvent, TargetResolution


class ExplicitPathTests(unittest.TestCase):
    def setUp(self):
        self.calls = []

    def existing_file(self, path):
        self.calls.append(path)
        return FileCheck(True, True)

    def test_absolute_file_is_inspected_and_returned_without_guessing(self):
        result = validate_explicit_paths([r"C:\files\input.txt"], self.existing_file)
        self.assertIsNone(result.rejection)
        self.assertEqual(result.path, PureWindowsPath(r"C:\files\input.txt"))
        self.assertEqual(self.calls, [result.path])

    def test_unicode_spaces_and_shell_metacharacters_remain_literal(self):
        for path in (
            r"C:\資料 æøå\input report.txt",
            r"C:\files\100% ready & Bob's ! ^ report.txt",
            r"C:\files\--looks-like-an-option.txt",
        ):
            with self.subTest(path=path):
                result = validate_explicit_paths([path], self.existing_file)
                self.assertEqual(str(result.path), path)
                self.assertIsNone(result.rejection)

    def test_zero_multiple_or_unparsed_delimiter_args_reject_before_inspection(self):
        for arguments in ([], [r"C:\a.txt", r"C:\b.txt"], ["--", r"C:\a.txt"],
                          r"C:\a.txt", None):
            with self.subTest(arguments=arguments):
                result = validate_explicit_paths(arguments, self.existing_file)
                self.assertEqual(result.rejection, "expected_one_path")
        self.assertFalse(self.calls)

    def test_relative_unc_and_device_paths_reject_before_inspection(self):
        for path in ("input.txt", r"C:input.txt", r"\input.txt",
                     r"\\server\share\input.txt", r"\\?\C:\input.txt",
                     r"\\.\C:\input.txt"):
            with self.subTest(path=path):
                result = validate_explicit_paths([path], self.existing_file)
                self.assertEqual(result.rejection, "absolute_local_path_required")
        self.assertFalse(self.calls)

    def test_unsafe_or_ambiguous_windows_path_syntax_rejects(self):
        for path in (
            r'C:\files\report.txt:stream', r'C:\files\..\report.txt',
            r'C:\files\.\report.txt', r'C:\files\NUL.txt',
            r'C:\files\COM1.txt', r'C:\files\LPT².txt',
            r'C:\files\file?.txt', r'C:\files\file*.txt',
            r'C:\files\trailing. ', "C:\\files\\report.txt\\",
        ):
            with self.subTest(path=path):
                result = validate_explicit_paths([path], self.existing_file)
                self.assertEqual(result.rejection, "unsupported_path")
        self.assertFalse(self.calls)

    def test_invalid_strings_are_not_unquoted_or_expanded(self):
        for path in ('"C:\\files\\input.txt"', "", "C:\\files\\nul\0.txt",
                     "C:\\files\\new\nline.txt", None, PureWindowsPath(r"C:\a.txt")):
            with self.subTest(path=path):
                result = validate_explicit_paths([path], self.existing_file)
                self.assertEqual(result.rejection, "invalid_path")
        self.assertFalse(self.calls)

    def test_missing_directory_and_reparse_file_are_distinct_rejections(self):
        for state, reason in (
            (FileCheck(False, False), "missing_file"),
            (FileCheck(True, False), "not_a_file"),
            (FileCheck(True, True, True), "unsupported_reparse_point"),
        ):
            with self.subTest(state=state):
                result = validate_explicit_paths([r"C:\files\input.txt"], lambda path: state)
                self.assertIsNone(result.path)
                self.assertEqual(result.rejection, reason)

    def test_stale_or_inaccessible_metadata_fail_closed_without_exception_text(self):
        for error, reason in (
            (FileNotFoundError("private"), "missing_file"),
            (NotADirectoryError("private"), "missing_file"),
            (PermissionError("private"), "file_access_denied"),
            (OSError("private"), "file_check_failed"),
            (RuntimeError("private"), "file_check_failed"),
        ):
            with self.subTest(error=type(error)):
                def inspect(path):
                    raise error
                result = validate_explicit_paths([r"C:\files\input.txt"], inspect)
                self.assertEqual(result.rejection, reason)
                self.assertNotIn("private", str(result))

    def test_malformed_filesystem_evidence_is_not_truthy_success(self):
        for state in (None, True, {"exists": True, "is_file": True},
                      FileCheck(1, True), FileCheck(True, "yes"), FileCheck(True, True, 0)):
            with self.subTest(state=state):
                result = validate_explicit_paths([r"C:\files\input.txt"], lambda path: state)
                self.assertEqual(result.rejection, "invalid_file_check")
                self.assertIsNone(result.path)


class ExplicitControllerTests(unittest.TestCase):
    def invoke(self, controller, inspector=lambda path: FileCheck(True, True), **context):
        return controller.handle_explicit(
            [r"C:\files\input.txt"], point=context.get("point", (-20, 40)),
            timestamp=context.get("timestamp", 10.0), inspect_file=inspector,
        )

    def test_explicit_only_controller_returns_shared_source_aware_dto(self):
        controller = InvocationController()
        result = self.invoke(controller)
        self.assertIsNone(result.rejection)
        self.assertIsInstance(result.target, TargetResolution)
        self.assertEqual(result.target.source, "shell_explicit")
        self.assertEqual(result.target.path, PureWindowsPath(r"C:\files\input.txt"))
        self.assertEqual(result.target.point, (-20, 40))
        self.assertEqual(result.target.timestamp, 10.0)
        self.assertEqual(result.target.window_id, 0)

    def test_invalid_validation_never_emits_a_target(self):
        controller = InvocationController()
        result = controller.handle_explicit(
            [r"C:\a.txt", r"C:\b.txt"], point=(0, 0), timestamp=1,
            inspect_file=lambda path: self.fail("multiple args inspected"),
        )
        self.assertIsNone(result.target)
        self.assertEqual(result.rejection, "expected_one_path")

    def test_context_is_finite_physical_coordinates_before_inspection(self):
        for changes in ({"point": (True, 1)}, {"point": (1,)}, {"point": (1.0, 2)},
                        {"timestamp": float("nan")}, {"timestamp": float("inf")},
                        {"timestamp": -1}, {"timestamp": True}):
            with self.subTest(changes=changes):
                result = self.invoke(InvocationController(),
                                     lambda path: self.fail("bad context inspected"), **changes)
                self.assertEqual(result.rejection, "invalid_invocation_context")
                self.assertIsNone(result.target)

    def test_cancel_during_file_inspection_discards_acceptance(self):
        controller = InvocationController()
        def inspect(path):
            controller.cancel()
            return FileCheck(True, True)
        result = self.invoke(controller, inspect)
        self.assertIsNone(result.target)
        self.assertEqual(result.rejection, "invocation_cancelled")

    def test_new_explicit_request_invalidates_old_hover_result(self):
        outputs = []
        class Resolver:
            def resolve(inner, mouse):
                outputs.append(self.invoke(controller))
                return TargetResolution(
                    PureWindowsPath(r"C:\files\hover.txt"), mouse.window_id,
                    mouse.point, mouse.timestamp,
                )
        controller = InvocationController(Resolver())
        self.assertIsNone(controller.handle(MouseEvent(1, (0, 0), 1, 123)))
        self.assertEqual(outputs[0].target.source, "shell_explicit")

    def test_new_hover_request_invalidates_old_explicit_result(self):
        class Resolver:
            def resolve(inner, mouse):
                return TargetResolution(
                    PureWindowsPath(r"C:\files\hover.txt"), mouse.window_id,
                    mouse.point, mouse.timestamp,
                )
        controller = InvocationController(Resolver())
        def inspect(path):
            self.assertIsNotNone(controller.handle(MouseEvent(1, (0, 0), 11, 123)))
            return FileCheck(True, True)
        result = self.invoke(controller, inspect)
        self.assertIsNone(result.target)
        self.assertEqual(result.rejection, "invocation_cancelled")

    def test_explicit_calls_do_not_apply_mouse_debounce(self):
        controller = InvocationController()
        self.assertIsNotNone(self.invoke(controller).target)
        self.assertIsNotNone(self.invoke(controller).target)

    def test_hover_resolver_cannot_mislabel_explicit_target(self):
        class Resolver:
            def resolve(inner, mouse):
                return TargetResolution(
                    PureWindowsPath(r"C:\files\input.txt"), mouse.window_id,
                    mouse.point, mouse.timestamp, source="shell_explicit",
                )
        controller = InvocationController(Resolver())
        self.assertIsNone(controller.handle(MouseEvent(1, (0, 0), 1, 123)))
