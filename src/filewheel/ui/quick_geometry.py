"""Stable logical hit regions for the 240px Quick prototype; independent of optics."""
import math

SIZE = 240
CENTER = 120
INNER = 40
OUTER = 110


def inside_boundary(x, y):
    """Circular window interaction boundary; center is inside, even with no options."""
    return (all(type(value) in (int, float) and math.isfinite(value) for value in (x, y))
            and math.hypot(x - CENTER, y - CENTER) <= OUTER)


def hit_test(x, y, count):
    if not all(type(value) in (int, float) and math.isfinite(value) for value in (x, y)):
        return -1
    radius = math.hypot(x - CENTER, y - CENTER)
    if radius < INNER:
        return -2
    if radius > OUTER or type(count) is not int or count <= 0:
        return -1
    angle = (math.degrees(math.atan2(y - CENTER, x - CENTER)) + 90) % 360
    return min(count - 1, int(angle * count / 360))
