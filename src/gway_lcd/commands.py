"""Gway command adapter for LCD operations."""

from __future__ import annotations

from .device import LCD
from .discovery import create_backend, scan


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
    address: str | None = None,
    bus: int = 1,
    columns: int = 16,
    rows: int = 2,
    driver: str = "auto",
) -> dict[str, object]:
    """Write the high/top and low/bottom display rows."""
    hi = _coalesce(hi, high)
    lo = _coalesce(lo, low)
    lcd = _lcd(address, bus, columns, rows, driver)
    lcd.write(hi, lo)
    return {**lcd.status(), "hi": hi, "lo": lo}


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
        if address == 0x3E:
            driver = "aip31068"
        else:
            driver = "pcf8574"
        devices.append({"address": f"0x{address:02x}", "driver": driver})
    return {
        "bus": bus,
        "addresses": [device["address"] for device in devices],
        "devices": devices,
    }
