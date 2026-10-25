"""Physical screen coordinates and monotonic timestamps cross the platform seam."""

from dataclasses import dataclass
from pathlib import PureWindowsPath
from typing import Literal, Protocol


@dataclass(frozen=True)
class MouseEvent:
    """A middle-button down; sequence increases within one source lifetime."""

    sequence: int
    point: tuple[int, int]
    timestamp: float
    window_id: int
    injected: bool = False


@dataclass(frozen=True)
class TargetResolution:
    """Adapter-attested filesystem file identity, never a selected-item guess.

    For explorer_hover the adapter must prove Explorer content provenance,
    point/bounds correspondence, Shell identity and current file existence/type.
    For shell_explicit the controller validates the explicitly supplied path;
    window_id is zero because no Explorer provenance inference is required.
    user_confirmed_candidate means explicit user consent to a displayed
    provisional path plus file revalidation, never proven hover identity.
    All sources return this DTO for the same UI consumer.
    PureWindowsPath keeps Windows path semantics in Linux contract tests.
    """

    path: PureWindowsPath
    window_id: int
    point: tuple[int, int]
    timestamp: float
    source: Literal["explorer_hover", "shell_explicit", "user_confirmed_candidate"] = "explorer_hover"

    def __post_init__(self) -> None:
        if not isinstance(self.path, PureWindowsPath) or not self.path.is_absolute():
            raise ValueError("resolution requires an absolute Windows path")


class TargetResolver(Protocol):
    def resolve(self, event: MouseEvent) -> TargetResolution | None:
        """Return only a proven file under this event's point; ambiguity returns None."""
        ...
