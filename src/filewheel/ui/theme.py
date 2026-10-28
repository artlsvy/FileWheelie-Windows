"""Restrained forest, ivory and brass roles shared by all popup stages.

The palette is a design choice, not an accessibility claim about native Windows.
Contrast calculations cover opaque role pairs; focus/hover retain readable text.
"""

import re
from dataclasses import dataclass
from functools import lru_cache


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


def normalize_accent(color):
    if color is None:
        return None
    if not isinstance(color, str) or re.fullmatch(r'#[0-9a-fA-F]{6}', color) is None:
        raise ValueError('Accent must be an RGB hex color')
    return color.upper()


def mix(first, second, amount):
    return '#' + ''.join(f'{round(int(first[i:i+2], 16) * (1-amount) + int(second[i:i+2], 16) * amount):02X}'
                         for i in (1, 3, 5))


def composite(color, backdrop, alpha=216 / 255):
    return mix(backdrop, color, alpha)


def _surfaces(base):
    return {'surface': base, 'top': mix(base, '#FFFFFF', .08), 'bottom': mix(base, '#000000', .06),
                'hover': mix(base, '#FFFFFF', .04), 'lensTop': mix(base, '#FFFFFF', .10),
                'lensMid': mix(base, '#FFFFFF', .04), 'lensBottom': mix(base, '#000000', .04)}


@lru_cache(maxsize=128)
def _custom_palette(color):
    # Keep the chosen hue. If needed, adjust its lightness just enough for one
    # opaque foreground to work over EVERY material and either desktop extreme.
    # 216/255 is the wheel's least opaque material; the lens/pill are denser.
    for step in range(101):
        candidates = []
        for foreground, target in (('#000000', '#FFFFFF'), ('#FFFFFF', '#000000')):
            surfaces = _surfaces(mix(color, target, step / 100))
            score = min(contrast_ratio(foreground, composite(value, backdrop))
                        for value in surfaces.values() for backdrop in ('#000000', '#FFFFFF'))
            if score >= 4.5:
                candidates.append((score, foreground, surfaces))
        if candidates:
            _, foreground, surfaces = max(candidates, key=lambda item: item[0])
            return dict(surfaces, text=foreground, accent=foreground, outline=foreground,
                        glare='#FFFFFF', reflection='#FFFFFF', shade=foreground,
                        muted=foreground, action=surfaces['hover'], on_action=foreground,
                        error=foreground)
    raise AssertionError('Black/white endpoint must produce a readable palette')


def glass_palette(color=None, dark=False):
    color = normalize_accent(color)
    if color is not None:
        return dict(_custom_palette(color))
    # Preserve the shipped material, including reflections, when reset/default.
    theme = DARK if dark else LIGHT
    return {'surface': theme.surface, 'text': theme.text, 'muted': theme.muted,
                'outline': '#96B69A' if dark else '#8B9478', 'accent': '#D6BF83' if dark else '#65532A',
                'top': '#304637' if dark else '#FFFDF3', 'bottom': '#172B23' if dark else '#E0E2CD',
                'hover': theme.hover, 'lensTop': '#4C624A' if dark else '#FFFFED',
                'lensMid': '#354E3B' if dark else '#E6E9D5', 'lensBottom': '#2B4231' if dark else '#CDD4B8',
                'glare': '#E5EBD8' if dark else '#FFFFFF', 'reflection': '#9EB29B' if dark else '#FFFFFF',
                'shade': '#6A865F' if dark else '#7D805F', 'action': theme.action,
                'on_action': theme.on_action, 'error': theme.error}


def accented_theme(color, dark=False):
    color = normalize_accent(color)
    if color is None:
        return DARK if dark else LIGHT
    palette = glass_palette(color, dark)
    return WheelTheme(*(palette[key] for key in (
        'surface', 'text', 'muted', 'outline', 'accent', 'hover', 'action', 'on_action', 'error')))
