"""One-shot routing of untrusted Mouse3 candidates with source-aware validation.

Direct activation is the user's chosen personal workflow; it does not establish
trusted hover identity. Optional per-file confirmation remains available.
"""

import math
from dataclasses import dataclass, field, replace
from pathlib import PureWindowsPath
from threading import Lock
from uuid import uuid4

from filewheel.core.explicit_paths import ExplicitInvocationResult
from filewheel.core.index_mapping import assess_index_mapping


def _time(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


@dataclass(frozen=True)
class ExperimentalCandidate:
    path: PureWindowsPath
    point: tuple[int, int]
    event_timestamp: float
    captured_at: float
    token: str = field(default_factory=lambda: uuid4().hex)

    def __post_init__(self):
        if (
            not isinstance(self.path, PureWindowsPath)
            or not self.path.is_absolute()
            or not isinstance(self.point, tuple)
            or len(self.point) != 2
            or any(type(value) is not int for value in self.point)
            or not _time(self.event_timestamp)
            or not _time(self.captured_at)
            or not 0 <= self.captured_at - self.event_timestamp <= 0.5
            or not isinstance(self.token, str)
            or not self.token
        ):
            raise ValueError("Invalid experimental candidate")


def candidate_from_record(record: dict, *, now: float) -> ExperimentalCandidate | None:
    """Reassess raw copied evidence; supplied mapping/verified flags are ignored."""
    mapping = assess_index_mapping(record, now=now)
    if mapping["status"] != "provisional" or record.get("snapshot_stable") is not True:
        return None
    checks = mapping["checks"]
    required = (
        "explorer_provenance",
        "fresh",
        "geometry_valid",
        "ancestry_provenance",
        "candidate_lookup_complete",
        "index_in_range",
        "active_view_associated",
        "native_index_path_match",
        "native_regular_file",
        "native_snapshot_stable",
        "native_local_fixed_drive",
    )
    if (
        any(checks.get(key) is not True for key in required)
        or checks.get("native_reparse_point") is not False
    ):
        return None
    try:
        return ExperimentalCandidate(
            PureWindowsPath(mapping["candidate_path"]),
            tuple(record["point"]),
            record["timestamp_monotonic"],
            now,
        )
    except TypeError, ValueError:
        return None


class CandidateGate:
    """Consume one candidate before file validation, without attesting identity.

    New offers/cancellation invalidate late inspection. Direct activation requires
    the original event to remain fresh; optional confirmation has a 30-second TTL.
    Both routes preserve their explicit source instead of claiming explorer_hover.
    """

    def __init__(self, *, ttl: float = 30):
        if not _time(ttl) or not 0 < ttl <= 30:
            raise ValueError("Candidate lifetime must be positive and at most 30 seconds")
        self.ttl = ttl
        self._lock = Lock()
        self._candidate = None
        self._generation = 0

    def offer(self, candidate: ExperimentalCandidate | None):
        if candidate is not None and not isinstance(candidate, ExperimentalCandidate):
            raise TypeError("Only experimental candidates may be offered")
        with self._lock:
            self._generation += 1
            self._candidate = candidate
        return candidate

    def cancel(self):
        self.offer(None)

    def is_current(self, token, *, now: float) -> bool:
        """Ignore queued stale UI callbacks without consuming a valid offer."""
        with self._lock:
            candidate = self._candidate
            return (
                candidate is not None
                and isinstance(token, str)
                and token == candidate.token
                and _time(now)
                and 0 <= now - candidate.captured_at <= self.ttl
            )

    def confirm(self, token, controller, inspect_file, *, now: float) -> ExplicitInvocationResult:
        return self._route(token, controller, inspect_file, now=now, confirmed=True)

    def activate(self, token, controller, inspect_file, *, now: float) -> ExplicitInvocationResult:
        """Personal direct-open route: fresh evidence plus controller validation."""
        return self._route(token, controller, inspect_file, now=now, confirmed=False)

    def _route(self, token, controller, inspect_file, *, now, confirmed):
        with self._lock:
            candidate = self._candidate
            if candidate is None or not isinstance(token, str) or token != candidate.token:
                return ExplicitInvocationResult(None, "candidate_not_current")
            # Matching tokens are consumed even when expired/context is invalid.
            self._candidate = None
            self._generation += 1
            generation = self._generation
            if not _time(now) or not 0 <= now - candidate.captured_at <= self.ttl:
                return ExplicitInvocationResult(None, "candidate_expired")
            if not confirmed and not 0 <= now - candidate.event_timestamp <= 0.5:
                return ExplicitInvocationResult(None, "candidate_expired")
        result = controller.handle_explicit(
            [str(candidate.path)], point=candidate.point, timestamp=now, inspect_file=inspect_file
        )
        with self._lock:
            if generation != self._generation:
                return ExplicitInvocationResult(None, "candidate_superseded")
            if result.target is None:
                return result
            return ExplicitInvocationResult(
                replace(result.target, source=("user_confirmed_candidate" if confirmed
                                               else "experimental_candidate")), None
            )
