from itertools import islice

import pytest

from gway_lcd.layout import scroll_windows, split_text, wrap_text


def test_split_text_uses_exact_display_width():
    assert split_text("abcdefghijklmnopQRST", 16) == (
        "abcdefghijklmnop",
        "QRST",
    )


def test_wrap_text_prefers_whitespace_before_width():
    assert wrap_text("alpha beta gamma", 10) == ("alpha beta", "gamma")


def test_wrap_text_falls_back_to_exact_split_without_whitespace():
    assert wrap_text("abcdefghijklmnopQRST", 16) == (
        "abcdefghijklmnop",
        "QRST",
    )


def test_scroll_windows_moves_one_character_and_has_space_seam():
    frames = list(islice(scroll_windows("abcdef", 4), 7))
    assert frames == ["abcd", "bcde", "cdef", "def ", "ef a", "f ab", " abc"]


def test_scroll_windows_keeps_short_text_stable():
    frames = list(islice(scroll_windows("ready", 16), 3))
    assert frames == ["ready", "ready", "ready"]


@pytest.mark.parametrize("function", [split_text, wrap_text, scroll_windows])
def test_layout_rejects_invalid_width(function):
    with pytest.raises(ValueError, match="width must be at least 1"):
        next(function("text", 0)) if function is scroll_windows else function("text", 0)
