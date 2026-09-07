"""Text layout and marquee helpers for character LCDs."""

from __future__ import annotations

import time
from collections.abc import Iterator


def split_text(text: str, width: int) -> tuple[str, str]:
    """Split text exactly at the physical row width."""
    if width < 1:
        raise ValueError("width must be at least 1")
    return text[:width], text[width:]


def wrap_text(text: str, width: int) -> tuple[str, str]:
    """Split text at the nearest whitespace at or before the row width."""
    if width < 1:
        raise ValueError("width must be at least 1")
    if len(text) <= width:
        return text, ""

    boundary = text.rfind(" ", 0, width + 1)
    if boundary <= 0:
        return split_text(text, width)
    return text[:boundary].rstrip(), text[boundary + 1 :].lstrip()


def scroll_windows(text: str, width: int) -> Iterator[str]:
    """Yield a smooth cyclic marquee with one blank character at the seam."""
    if width < 1:
        raise ValueError("width must be at least 1")
    if len(text) <= width:
        while True:
            yield text

    cycle = f"{text} "
    repeated = cycle * ((width // len(cycle)) + 2)
    while True:
        for offset in range(len(cycle)):
            source = repeated[offset:] + repeated[:offset]
            yield source[:width]


def render_rows(
    lcd,
    hi: str,
    lo: str,
    *,
    scroll: bool = False,
    speed: float = 2.0,
) -> None:
    """Render two rows once, or continuously as synchronized marquees."""
    if speed <= 0:
        raise ValueError("speed must be greater than zero")
    if not scroll or (len(hi) <= lcd.columns and len(lo) <= lcd.columns):
        lcd.write(hi, lo)
        return

    hi_frames = scroll_windows(hi, lcd.columns)
    lo_frames = scroll_windows(lo, lcd.columns)
    while True:
        lcd.write(next(hi_frames), next(lo_frames))
        time.sleep(speed)
