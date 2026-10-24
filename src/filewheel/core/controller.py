"""Synchronous routing; a caller-owned worker performs potentially slow resolution."""

from threading import Lock

from filewheel.core.models import MouseEvent, TargetResolution, TargetResolver


class InvocationController:
    """One source lifetime per controller. New events/cancel invalidate pending results.

    Resolver exceptions fail closed. Calls can overlap; the adapter must implement
    its own COM thread ownership. No lock is held while resolving.
    """

    def __init__(self, resolver: TargetResolver, debounce_seconds: float = 0.15):
        if debounce_seconds < 0:
            raise ValueError("debounce_seconds must be nonnegative")
        self._resolver = resolver
        self._debounce = debounce_seconds
        self._lock = Lock()
        self._generation = 0
        self._last_sequence = -1
        self._last_timestamp = float("-inf")

    def cancel(self) -> None:
        with self._lock:
            self._generation += 1

    def handle(self, event: MouseEvent) -> TargetResolution | None:
        with self._lock:
            if event.sequence <= self._last_sequence:
                return None
            self._last_sequence = event.sequence
            self._generation += 1
            generation = self._generation
            if event.injected or event.timestamp - self._last_timestamp < self._debounce:
                return None
            self._last_timestamp = event.timestamp
        try:
            result = self._resolver.resolve(event)
        except Exception:
            return None
        with self._lock:
            if generation != self._generation or result is None:
                return None
            if (
                result.point != event.point
                or result.window_id != event.window_id
                or result.timestamp != event.timestamp
                or result.source != "explorer_hover"
            ):
                return None
            return result
