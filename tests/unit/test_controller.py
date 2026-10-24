import unittest
from dataclasses import replace
from pathlib import PureWindowsPath

from filewheel.core.controller import InvocationController
from filewheel.core.models import MouseEvent, TargetResolution


def event(sequence=1, timestamp=10.0, point=(-20, 40)):
    return MouseEvent(sequence, point, timestamp, window_id=123)


def resolution(mouse, name="hovered.txt"):
    return TargetResolution(
        PureWindowsPath("C:/files") / name, mouse.window_id, mouse.point, mouse.timestamp
    )


class FakeResolver:
    def __init__(self, action):
        self.action = action
        self.calls = []

    def resolve(self, mouse):
        self.calls.append(mouse)
        return self.action(mouse)


class ControllerTests(unittest.TestCase):
    def test_hovered_file_wins_when_other_file_is_selected(self):
        selected = PureWindowsPath("C:/files/selected.txt")
        resolver = FakeResolver(resolution)
        result = InvocationController(resolver).handle(event())
        self.assertEqual(result.path, PureWindowsPath("C:/files/hovered.txt"))
        self.assertNotEqual(result.path, selected)
        self.assertEqual(resolver.calls, [event()])

    def test_none_never_falls_back_to_previous_target(self):
        resolver = FakeResolver(lambda mouse: resolution(mouse) if mouse.sequence == 1 else None)
        controller = InvocationController(resolver)
        self.assertIsNotNone(controller.handle(event()))
        self.assertIsNone(controller.handle(event(2, 11)))

    def test_duplicate_and_older_sequences_are_ignored(self):
        resolver = FakeResolver(resolution)
        controller = InvocationController(resolver)
        controller.handle(event(2))
        self.assertIsNone(controller.handle(event(2, 11)))
        self.assertIsNone(controller.handle(event(1, 12)))
        self.assertEqual(len(resolver.calls), 1)

    def test_debounce_then_later_click(self):
        resolver = FakeResolver(resolution)
        controller = InvocationController(resolver)
        controller.handle(event())
        self.assertIsNone(controller.handle(event(2, 10.05)))
        self.assertIsNotNone(controller.handle(event(3, 10.2)))
        self.assertEqual(len(resolver.calls), 2)

    def test_cancel_during_resolution_discards_result(self):
        def action(mouse):
            controller.cancel()
            return resolution(mouse)
        controller = InvocationController(FakeResolver(action))
        self.assertIsNone(controller.handle(event()))

    def test_newer_reentrant_event_invalidates_old_result(self):
        def action(mouse):
            if mouse.sequence == 1:
                self.assertIsNotNone(controller.handle(event(2, 11)))
            return resolution(mouse)
        controller = InvocationController(FakeResolver(action))
        self.assertIsNone(controller.handle(event()))

    def test_injected_event_does_not_resolve(self):
        resolver = FakeResolver(resolution)
        controller = InvocationController(resolver)
        self.assertIsNone(controller.handle(replace(event(), injected=True)))
        self.assertFalse(resolver.calls)

    def test_timeout_fails_closed(self):
        def timeout(mouse):
            raise TimeoutError("fake UIA timeout")
        self.assertIsNone(InvocationController(FakeResolver(timeout)).handle(event()))

    def test_mismatched_evidence_fails_closed(self):
        for changes in ({"point": (0, 0)}, {"window_id": 5}, {"timestamp": 1}):
            with self.subTest(changes=changes):
                resolver = FakeResolver(lambda mouse: replace(resolution(mouse), **changes))
                self.assertIsNone(InvocationController(resolver).handle(event()))

    def test_relative_path_is_rejected(self):
        with self.assertRaises(ValueError):
            TargetResolution(PureWindowsPath("relative.txt"), 123, (0, 0), 10)

    def test_decreasing_timestamp_is_rejected(self):
        controller = InvocationController(FakeResolver(resolution))
        controller.handle(event())
        self.assertIsNone(controller.handle(event(2, 9)))


if __name__ == "__main__":
    unittest.main()
