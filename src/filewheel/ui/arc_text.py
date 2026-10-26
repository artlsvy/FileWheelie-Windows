"""Pure tangent geometry for readable glyphs on a circular baseline."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ArcGlyph:
    text: str
    x: float
    y: float
    rotation: float
    advance: float


def arc_direction(center_degrees):
    """Bottom-half labels run counterclockwise so they are not upside down."""
    return -1 if math.sin(math.radians(center_degrees)) > 1e-9 else 1


def arc_glyphs(text, advances, center_degrees, radius, *, center=(162, 162)):
    """Center measured glyph advances around an arc; no Qt rendering dependency."""
    if (len(text) != len(advances) or not math.isfinite(radius) or radius <= 0
            or not math.isfinite(center_degrees) or len(center) != 2
            or not all(math.isfinite(value) for value in center)):
        raise ValueError('Measured glyphs and finite circular geometry required')
    if any(not math.isfinite(value) or value < 0 for value in advances):
        raise ValueError('Finite nonnegative glyph advances required')
    direction = arc_direction(center_degrees)
    cursor = -sum(advances) / 2
    result = []
    for glyph, advance in zip(text, advances):
        angle = center_degrees + math.degrees(direction * (cursor + advance / 2) / radius)
        radians = math.radians(angle)
        rotation = (angle + direction * 90 + 180) % 360 - 180
        result.append(ArcGlyph(glyph, center[0] + radius * math.cos(radians),
                               center[1] + radius * math.sin(radians), rotation, advance))
        cursor += advance
    return tuple(result)
