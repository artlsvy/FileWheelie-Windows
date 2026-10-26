"""Presentation states do not own, stop or infer progress of conversion jobs."""
from dataclasses import dataclass
from enum import StrEnum

from filewheel.ui.placement import Rect, popup_position


class ProgressMode(StrEnum):
    SELECTING = 'selecting'
    CONVERTING_EXPANDED = 'converting_expanded'
    CONVERTING_COMPACT = 'converting_compact'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


@dataclass
class ProgressPresentation:
    mode: ProgressMode = ProgressMode.SELECTING
    compact: bool = False

    def start(self):
        self.mode, self.compact = ProgressMode.CONVERTING_EXPANDED, False

    def collapse(self):
        if self.mode != ProgressMode.SELECTING:
            self.compact = True
            if self.mode == ProgressMode.CONVERTING_EXPANDED:
                self.mode = ProgressMode.CONVERTING_COMPACT

    def expand(self):
        self.compact = False
        if self.mode == ProgressMode.CONVERTING_COMPACT:
            self.mode = ProgressMode.CONVERTING_EXPANDED

    def complete(self, *, failed=False, cancelled=False):
        self.mode = ProgressMode.CANCELLED if cancelled else ProgressMode.FAILED if failed else ProgressMode.SUCCEEDED


def progress_position(available: Rect, size=(248, 60), margin=16):
    """Bottom-right of the original monitor work area, already Qt logical units."""
    return popup_position((available.x + available.width - size[0] / 2 - margin,
                           available.y + available.height - size[1] / 2 - margin),
                          available, size, margin)
