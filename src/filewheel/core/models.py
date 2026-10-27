"""Physical screen coordinates and monotonic timestamps cross the platform seam."""

from dataclasses import dataclass
from pathlib import PureWindowsPath
from typing import Literal, Protocol

LLMHF_INJECTED = 0x00000001
LLMHF_LOWER_IL_INJECTED = 0x00000002


@dataclass(frozen=True)
class MouseEvent:
    """A middle-button down; sequence increases within one source lifetime."""

    sequence: int
    point: tuple[int, int]
    timestamp: float
    window_id: int
    injected: bool = False
    native_flags: int | None = None

    def __post_init__(self) -> None:
        if type(self.injected) is not bool:
            raise ValueError("injected must be a bool")
        if self.native_flags is not None:
            if type(self.native_flags) is not int or not 0 <= self.native_flags <= 0xFFFFFFFF:
                raise ValueError("native_flags must be a DWORD integer or None")
            if self.native_flags & (LLMHF_INJECTED | LLMHF_LOWER_IL_INJECTED):
                object.__setattr__(self, "injected", True)

    @property
    def lower_integrity_injected(self) -> bool:
        return self.native_flags is not None and bool(self.native_flags & LLMHF_LOWER_IL_INJECTED)


def mouse_event_permitted(event: MouseEvent, *, allow_injected: bool = False) -> bool:
    """Permit physical input or explicitly opted-in injection without a lower-integrity flag.

    Missing native flags cannot establish the integrity of legacy injected input.
    Unknown native bits and inconsistent metadata fail closed.
    """
    if not isinstance(event, MouseEvent) or type(event.injected) is not bool:
        return False
    flags = event.native_flags
    if flags is None:
        return not event.injected
    if type(flags) is not int or not 0 <= flags <= 0xFFFFFFFF:
        return False
    if flags & ~(LLMHF_INJECTED | LLMHF_LOWER_IL_INJECTED):
        return False
    if flags & LLMHF_LOWER_IL_INJECTED:
        return False
    if flags & LLMHF_INJECTED:
        return event.injected and allow_injected is True
    return not event.injected


@dataclass(frozen=True)
class TargetResolution:
    """Controller-validated file path, with invocation provenance kept explicit.

    For explorer_hover the adapter must prove Explorer content provenance,
    point/bounds correspondence, Shell identity and current file existence/type.
    For shell_explicit the controller validates the explicitly supplied path;
    window_id is zero because no Explorer provenance inference is required.
    user_confirmed_candidate means explicit user consent to a displayed
    provisional path plus file revalidation, never proven hover identity.
    experimental_candidate is a provisional Mouse3 path revalidated for direct
    popup activation under the user's personal preference; no hover identity or
    per-file confirmation is claimed. All sources share the same UI consumer.
    PureWindowsPath keeps Windows path semantics explicit in controller contracts.
    """

    path: PureWindowsPath
    window_id: int
    point: tuple[int, int]
    timestamp: float
    source: Literal[
        "explorer_hover", "shell_explicit", "user_confirmed_candidate", "experimental_candidate"
    ] = "explorer_hover"

    def __post_init__(self) -> None:
        if not isinstance(self.path, PureWindowsPath) or not self.path.is_absolute():
            raise ValueError("resolution requires an absolute Windows path")


class TargetResolver(Protocol):
    def resolve(self, event: MouseEvent) -> TargetResolution | None:
        """Return only a proven file under this event's point; ambiguity returns None."""
        ...
