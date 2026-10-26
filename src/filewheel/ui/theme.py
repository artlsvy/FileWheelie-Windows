"""Restrained forest, ivory and brass roles shared by all popup stages.

The palette is a design choice, not an accessibility claim about native Windows.
Contrast calculations cover opaque role pairs; focus/hover retain readable text.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WheelTheme:
    surface: str
    text: str
    muted: str
    outline: str
    accent: str
    hover: str
    action: str
    on_action: str
    error: str


LIGHT = WheelTheme(
    '#F4F0E5', '#20392F', '#526253', '#68745C', '#5F512A', '#E3E5CF',
    '#203D32', '#F6F1E6', '#973D35',
)
DARK = WheelTheme(
    '#182C24', '#F3ECDD', '#C1C9B7', '#99A98E', '#D6BF83', '#304A38',
    '#D6BF83', '#182C24', '#F2B3A9',
)


def contrast_ratio(first, second):
    def luminance(color):
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4
                  for value in channels]
        return sum(value * weight for value, weight in zip(linear, (.2126, .7152, .0722)))
    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + .05) / (darker + .05)
