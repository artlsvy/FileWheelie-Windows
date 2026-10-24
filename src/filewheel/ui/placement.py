"""Desktop placement with explicit screen origins; no global-DPR division."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float


def physical_to_logical(point, physical: Rect, logical: Rect):
    if min(physical.width, physical.height, logical.width, logical.height) <= 0:
        raise ValueError("positive monitor dimensions required")
    return (logical.x + (point[0] - physical.x) * logical.width / physical.width,
            logical.y + (point[1] - physical.y) * logical.height / physical.height)


def popup_position(point, available: Rect, size=(324, 324), margin=6):
    if not all(math.isfinite(v) for v in (*point, available.x, available.y,
                                         available.width, available.height, *size, margin)):
        raise ValueError("finite geometry required")
    if min(available.width, available.height, *size) <= 0 or margin < 0:
        raise ValueError("positive geometry required")
    # Tiny work areas cannot contain a fixed-size window: anchor to their origin.
    def axis(center, start, length, extent):
        if length < extent + margin * 2:
            return round(start)
        return round(min(max(center - extent / 2, start + margin),
                         start + length - extent - margin))
    return (axis(point[0], available.x, available.width, size[0]),
            axis(point[1], available.y, available.height, size[1]))
