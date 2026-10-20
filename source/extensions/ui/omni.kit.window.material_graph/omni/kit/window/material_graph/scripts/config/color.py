"""Implement material graph extension logic for `config/color.py`."""

import colorsys
import hashlib
from typing import Sequence


def rgb_to_abgr(rgb: int) -> int:
    """Convert an RGB int to ABGR for omni.ui."""
    a = 0xFF
    b = rgb & 0xFF
    g = (rgb >> 8) & 0xFF
    r = (rgb >> 16) & 0xFF
    return (a << 24) | (b << 16) | (g << 8) | r


def tuple_to_abgr(value: Sequence[float]) -> int:
    """Convert a 3-float RGB tuple to ABGR (normalizes values > 1)."""
    if not (value and len(value) == 3):
        return 0x00000000

    r, g, b = (max(0.0, x) for x in value)

    max_val = max(r, g, b)
    if max_val > 1.0:
        r, g, b = (x / max_val for x in (r, g, b))

    r, g, b = (int(round(x * 255)) for x in (r, g, b))

    a = 0xFF
    return (a << 24) | (b << 16) | (g << 8) | r


def string_to_random_abgr(value: str) -> int:
    """Return a stable pseudo-random saturated ABGR color for a string."""
    if not value:
        value = "default"
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    hue = digest[0] / 255.0
    saturation = 0.85
    brightness = 0.95
    r_f, g_f, b_f = colorsys.hsv_to_rgb(hue, saturation, brightness)
    r = int(round(r_f * 255))
    g = int(round(g_f * 255))
    b = int(round(b_f * 255))
    a = 0xFF
    return (a << 24) | (b << 16) | (g << 8) | r
