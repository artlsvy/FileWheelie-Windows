"""Synchronous routing; a caller-owned worker performs potentially slow resolution."""

import math
from collections.abc import Sequence
from threading import Lock

from filewheel.core.explicit_paths import (
    ExplicitInvocationResult,
    FileInspector,
    validate_explicit_paths,
)
from filewheel.core.models import (
    MouseEvent,
    TargetResolution,
    TargetResolver,
    mouse_event_permitted,
)


class InvocationController:
    """One source lifetime per controller. New events/cancel invalidate pending results.

    Resolver exceptions fail closed. Calls can overlap; the adapter must implement
    its own COM thread ownership. No lock is held while resolving.
    """

    def __init__(self, resolver: TargetResolver | None = None, debounce_seconds: float = 0.15,
                 *, allow_injected_candidates: bool = False):
        if debounce_seconds < 0:
            raise ValueError("debounce_seconds must be nonnegative")
        self._resolver = resolver
        self._allow_injected_candidates = allow_injected_candidates is True
        self._debounce = debounce_seconds
        self._lock = Lock()
        self._generation = 0
        self._last_sequence = -1
        self._last_timestamp = float("-inf")

    def cancel(self) -> None:
        with self._lock:
            self._generation += 1

    def handle_explicit(
        self, arguments: Sequence[str], *, point: tuple[int, int], timestamp: float,
        inspect_file: FileInspector,
    ) -> ExplicitInvocationResult:
        """Route one Shell-supplied path through the shared target DTO boundary.

        Explicit requests replace pending hover/explicit work without applying
        mouse sequence or debounce rules. Inspection runs outside the lock;
        cancellation or a newer request discards its eventual result.
        """
        with self._lock:
            self._generation += 1
            generation = self._generation
        if (
            not isinstance(point, (tuple, list)) or len(point) != 2
            or any(type(coordinate) is not int for coordinate in point)
            or type(timestamp) not in (int, float) or not math.isfinite(timestamp)
            or timestamp < 0
        ):
            return ExplicitInvocationResult(None, "invalid_invocation_context")
        validation = validate_explicit_paths(arguments, inspect_file)
        with self._lock:
            if generation != self._generation:
                return ExplicitInvocationResult(None, "invocation_cancelled")
            if validation.path is None:
                return ExplicitInvocationResult(None, validation.rejection)
            target = TargetResolution(
                validation.path, window_id=0, point=tuple(point), timestamp=timestamp,
                source="shell_explicit",
            )
            return ExplicitInvocationResult(target, None)

    def handle(self, event: MouseEvent) -> TargetResolution | None:
        with self._lock:
            if event.sequence <= self._last_sequence:
                return None
            self._last_sequence = event.sequence
            self._generation += 1
            generation = self._generation
            if (not mouse_event_permitted(event, allow_injected=self._allow_injected_candidates)
                    or event.timestamp - self._last_timestamp < self._debounce):
                return None
            self._last_timestamp = event.timestamp
        try:
            result = self._resolver.resolve(event)
        except Exception:  # noqa: BLE001 - resolver boundary fails closed
            return None
        with self._lock:
            # Opt-in permits evidence collection, never a trusted injected target.
            if event.injected or generation != self._generation or result is None:
                return None
            if (
                result.point != event.point
                or result.window_id != event.window_id
                or result.timestamp != event.timestamp
                or result.source != "explorer_hover"
            ):
                return None
            return result
