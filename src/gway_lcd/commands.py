"""Gway command adapter for LCD operations."""

from __future__ import annotations

from .device import LCD
from .discovery import create_backend, scan
from .layout import render_rows, split_text, wrap_text
from .standby import DEFAULT_HOLD, load_config, screens_from_config
from .standby import run as run_standby


def _address(value: str | int | None) -> int | None:
    if value in {None, "", "auto"}:
        return None
    return int(value, 0) if isinstance(value, str) else value


def _lcd(
    address: str | int | None = None,
    bus: int = 1,
    columns: int = 16,
    rows: int = 2,
    driver: str = "auto",
) -> LCD:
    return LCD(
        create_backend(
            driver=driver,
            address=_address(address),
            bus=bus,
            columns=columns,
            rows=rows,
        )
    )


def _coalesce(primary: str, alias: str | None) -> str:
    return primary if alias is None else alias


def _rows(
    *,
    hi: str,
    lo: str,
    high: str | None,
    low: str | None,
    wrap: str | None,
    split: str | None,
    columns: int,
) -> tuple[str, str]:
    if wrap is not None and split is not None:
        raise ValueError("--wrap and --split are mutually exclusive")
    hi = _coalesce(hi, high)
    lo = _coalesce(lo, low)
    if wrap is not None:
        if hi or lo:
            raise ValueError("--wrap cannot be combined with hi/lo text")
        return wrap_text(wrap, columns)
    if split is not None:
        if hi or lo:
            raise ValueError("--split cannot be combined with hi/lo text")
        return split_text(split, columns)
    return hi, lo


def show(
    text: str,
    line: int = 1,
    address: str | None = None,
    bus: int = 1,
    columns: int = 16,
    rows: int = 2,
    driver: str = "auto",
) -> dict[str, object]:
    """Write text to one display line."""
    lcd = _lcd(address, bus, columns, rows, driver)
    lcd.write_line(line, text)
    return {**lcd.status(), "line": line, "text": text}


def write(
    hi: str = "",
    lo: str = "",
    high: str | None = None,
    low: str | None = None,
    wrap: str | None = None,
    split: str | None = None,
    scroll: bool = False,
    speed: float = 2.0,
    address: str | None = None,
    bus: int = 1,
    columns: int = 16,
    rows: int = 2,
    driver: str = "auto",
) -> dict[str, object]:
    """Write two rows, optionally wrapping, splitting, or scrolling text."""
    hi, lo = _rows(
        hi=hi,
        lo=lo,
        high=high,
        low=low,
        wrap=wrap,
        split=split,
        columns=columns,
    )
    lcd = _lcd(address, bus, columns, rows, driver)
    render_rows(lcd, hi, lo, scroll=scroll, speed=speed)
    return {
        **lcd.status(),
        "hi": hi,
        "lo": lo,
        "scroll": scroll,
        "speed": speed,
    }


def standby(
    config: str | None = None,
    screen: str | None = None,
    hi: str = "",
    lo: str = "",
    high: str | None = None,
    low: str | None = None,
    wrap: str | None = None,
    split: str | None = None,
    hold: float = DEFAULT_HOLD,
    rotation: str | None = None,
    priority: int = 100,
    order: str | None = None,
    interval: float | None = None,
    once: bool = False,
    address: str | None = None,
    bus: int = 1,
    columns: int = 16,
    rows: int = 2,
    driver: str = "auto",
) -> dict[str, object]:
    """Display a named screen or run a configurable screen rotation."""
    hi, lo = _rows(
        hi=hi,
        lo=lo,
        high=high,
        low=low,
        wrap=wrap,
        split=split,
        columns=columns,
    )
    if (hi or lo) and screen is None:
        screen = "status"

    settings = load_config(config)
    screens, configured_hold = screens_from_config(
        settings,
        screen=screen,
        hi=hi,
        lo=lo,
        rotation=rotation,
        order=order,
        hold=hold,
        priority=priority,
    )
    default_hold = configured_hold if interval is None else interval
    standalone = screen is not None and rotation is None and order is None
    lcd = _lcd(address, bus, columns, rows, driver)
    result = run_standby(
        lcd,
        screens,
        default_hold=default_hold,
        once=once or standalone,
    )
    return {
        **lcd.status(),
        **result,
        "hold": default_hold,
        "rotation": rotation,
    }


def clear(
    address: str | None = None,
    bus: int = 1,
    columns: int = 16,
    rows: int = 2,
    driver: str = "auto",
) -> dict[str, object]:
    """Clear the display."""
    lcd = _lcd(address, bus, columns, rows, driver)
    lcd.clear()
    return lcd.status()


def status(
    address: str | None = None,
    bus: int = 1,
    columns: int = 16,
    rows: int = 2,
    driver: str = "auto",
) -> dict[str, object]:
    """Initialize the detected display and return its identity."""
    return _lcd(address, bus, columns, rows, driver).status()


def backlight(
    on: bool = True,
    address: str | None = None,
    bus: int = 1,
    columns: int = 16,
    rows: int = 2,
    driver: str = "auto",
) -> dict[str, object]:
    """Enable or disable a PCF8574 backpack backlight."""
    lcd = _lcd(address, bus, columns, rows, driver)
    lcd.backlight(on)
    return {**lcd.status(), "backlight": on}


def detect(bus: int = 1) -> dict[str, object]:
    """Detect supported Gway LCD hardware on an I2C bus."""
    addresses = scan(bus)
    devices: list[dict[str, str]] = []
    for address in sorted(addresses):
        driver = "aip31068" if address == 0x3E else "pcf8574"
        devices.append({"address": f"0x{address:02x}", "driver": driver})
    return {
        "bus": bus,
        "addresses": [device["address"] for device in devices],
        "devices": devices,
    }
