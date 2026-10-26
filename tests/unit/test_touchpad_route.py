"""Portable coverage of injected candidate routing; no native hook acceptance."""

import copy
import time
from pathlib import PureWindowsPath
from threading import Event
from unittest.mock import Mock

import pytest
from test_experimental_candidates import captured_record
from test_mouse_runtime import FakeBackend, record_fixture

from filewheel.core.controller import InvocationController
from filewheel.core.experimental import CandidateGate, candidate_from_record
from filewheel.core.explicit_paths import FileCheck
from filewheel.core.models import MouseEvent, TargetResolution
from filewheel.platforms.windows.mouse_runtime import MouseRuntime


def touchpad_record():
    record = captured_record()
    record.update(injected=True, native_flags=1)
    return record


def mouse_for(record):
    return MouseEvent(
        record["sequence"], tuple(record["point"]), record["timestamp_monotonic"],
        record["window"]["foreground_hwnd"], record["injected"],
        native_flags=record.get("native_flags"),
    )


@pytest.mark.parametrize("flags, opted_in, resolves", [
    (1, False, False), (1, True, True),
    (2, False, False), (2, True, False), (3, True, False),
])
def test_controller_collects_opted_in_evidence_but_never_trusts_injection(flags, opted_in, resolves):
    record = touchpad_record()
    record["native_flags"] = flags
    event = mouse_for(record)
    trusted = TargetResolution(
        PureWindowsPath(r"C:\fixture\project\tests\b.txt"),
        event.window_id, event.point, event.timestamp,
    )
    resolver = Mock()
    resolver.resolve.return_value = trusted
    controller = InvocationController(resolver, allow_injected_candidates=opted_in)
    assert controller.handle(event) is None
    assert resolver.resolve.call_args_list == ([((event,), {})] if resolves else [])


def test_opted_in_candidate_retains_flags_and_requires_confirmation():
    record = touchpad_record()
    now = record["timestamp_monotonic"] + 0.12
    assert candidate_from_record(record, now=now) is None
    candidate = candidate_from_record(record, now=now, allow_injected_candidates=True)
    assert candidate is not None
    assert candidate.native_flags == 1
    assert candidate.requires_confirmation
    assert not isinstance(candidate, TargetResolution)
    gate = CandidateGate()
    gate.offer(candidate)
    inspect = Mock(return_value=FileCheck(True, True))
    result = gate.activate(candidate.token, InvocationController(), inspect, now=now + 0.1)
    assert result.target is None
    assert result.rejection == "candidate_confirmation_required"
    inspect.assert_not_called()

    gate.offer(candidate)
    result = gate.confirm(candidate.token, InvocationController(), inspect, now=now + 1)
    assert result.target.path == candidate.path
    assert result.target.source == "user_confirmed_candidate"
    inspect.assert_called_once_with(candidate.path)
    assert gate.confirm(candidate.token, InvocationController(), inspect, now=now + 2).target is None


def test_injected_confirmation_revalidates_missing_file():
    record = touchpad_record()
    now = record["timestamp_monotonic"] + 0.12
    candidate = candidate_from_record(record, now=now, allow_injected_candidates=True)
    gate = CandidateGate()
    gate.offer(candidate)
    inspect = Mock(return_value=FileCheck(False, False))
    result = gate.confirm(candidate.token, InvocationController(), inspect, now=now + 1)
    assert result.target is None
    assert result.rejection == "missing_file"
    inspect.assert_called_once_with(candidate.path)


@pytest.mark.parametrize("injected, flags", [
    (True, 2), (True, 3), (True, None), (True, 0),
    (False, 1), (False, 2), (True, 5), (True, -1), (True, True),
])
def test_candidate_rejects_lower_legacy_mismatched_and_invalid_flags(injected, flags):
    record = touchpad_record()
    record.update(injected=injected, native_flags=flags)
    assert candidate_from_record(
        record, now=record["timestamp_monotonic"] + 0.12, allow_injected_candidates=True,
    ) is None


class ObservedBackend(FakeBackend):
    def __init__(self, record):
        super().__init__(record)
        self.completed = Event()
        self.allowed_preference = None

    def create_resolver(self, write, *, allow_injected_candidates=False):
        self.allowed_preference = allow_injected_candidates
        resolver = super().create_resolver(
            write, allow_injected_candidates=allow_injected_candidates,
        )
        backend = self

        class ObservedResolver:
            def resolve(self, event):
                try:
                    return resolver.resolve(event)
                finally:
                    backend.completed.set()

            def close(self):
                resolver.close()

        return ObservedResolver()


def runtime_result(record, event, *, opted_in=False, resolves=True, age=0.12, resolve_error=None):
    backend = ObservedBackend(record)
    backend.resolve_error = resolve_error
    candidates, errors = [], []
    runtime = MouseRuntime(
        candidates.append, errors.append, allow_injected_candidates=opted_in,
        _backend=backend, _clock=lambda: event.timestamp + age,
    )
    try:
        assert runtime.start()
        runtime._events.put(event)
        if resolves:
            assert backend.completed.wait(2)
        else:
            expires = time.monotonic() + 2
            while not runtime._events.empty() and time.monotonic() < expires:
                time.sleep(0.002)
            assert runtime._events.empty()
    finally:
        assert runtime.close(timeout=2)
    assert backend.allowed_preference is opted_in
    assert runtime._current_event is None
    assert backend.resolved.is_set() is resolves
    return candidates, errors


@pytest.mark.parametrize("flags, opted_in, resolves, count", [
    (None, False, True, 1), (0, False, True, 1),
    (1, False, False, 0), (1, True, True, 1),
    (2, False, False, 0), (2, True, False, 0),
    (3, False, False, 0), (3, True, False, 0),
])
def test_runtime_native_event_policy(flags, opted_in, resolves, count):
    record = record_fixture()
    record.update(injected=bool(flags), native_flags=flags)
    candidates, errors = runtime_result(record, mouse_for(record), opted_in=opted_in, resolves=resolves)
    assert errors == []
    assert len(candidates) == count
    if candidates:
        assert candidates[0].native_flags == (flags or 0)
        assert candidates[0].requires_confirmation is bool(flags)


@pytest.mark.parametrize("field, replacement", [
    ("sequence", 2), ("timestamp_monotonic", 99.0), ("point", [0, 0]),
    ("window_id", 999), ("native_flags", 0), ("physical_claim", False),
])
def test_runtime_binds_evidence_to_original_hook_event(field, replacement):
    record = touchpad_record()
    event = mouse_for(record)
    if field == "window_id":
        record["window"]["foreground_hwnd"] = replacement
    elif field == "physical_claim":
        record.update(injected=False, native_flags=0)
    else:
        record[field] = replacement
    candidates, errors = runtime_result(record, event, opted_in=True)
    assert candidates == []
    assert errors == []


def corrupt_evidence(record, defect):
    shell = record["shell_candidates"]["matching_windows"][0]
    if defect == "explorer":
        record["window"]["process_image"] = r"C:\other.exe"
    elif defect == "uia":
        record.pop("uia_ancestry")
    elif defect == "geometry":
        record["uia_ancestry"][0].pop("bounds")
    elif defect == "tab":
        shell.pop("active_view_association")
    elif defect == "native":
        shell.pop("native_view_candidate")
    elif defect == "path":
        shell["native_view_candidate"]["candidate_path"] = r"C:\wrong.txt"
    elif defect == "missing_file":
        shell["native_view_candidate"]["exists_regular_file"] = False
    elif defect == "unsafe_path":
        shell["native_view_candidate"]["candidate_path"] = r"C:\fixture\..\wrong.txt"
        shell["candidates"][-1]["candidate_path"] = r"C:\fixture\..\wrong.txt"
    elif defect == "snapshot":
        record["snapshot_stable"] = False
    else:
        raise AssertionError(defect)


@pytest.mark.parametrize("defect", [
    "explorer", "uia", "geometry", "tab", "native", "path", "missing_file",
    "unsafe_path", "snapshot", "stale",
])
def test_opt_in_preserves_all_evidence_rejections(defect):
    record = touchpad_record()
    age = 0.6 if defect == "stale" else 0.12
    if defect != "stale":
        corrupt_evidence(record, defect)
    assert candidate_from_record(
        record, now=record["timestamp_monotonic"] + age, allow_injected_candidates=True,
    ) is None
    candidates, errors = runtime_result(copy.deepcopy(record), mouse_for(record),
                                        opted_in=True, age=age)
    assert candidates == []
    assert errors == []


def test_runtime_clears_original_event_after_resolution_exception():
    record = touchpad_record()
    candidates, errors = runtime_result(record, mouse_for(record), opted_in=True,
                                        resolve_error=RuntimeError("private detail"))
    assert candidates == []
    assert errors == ["mouse_evidence: RuntimeError"]
