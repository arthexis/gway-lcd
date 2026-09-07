"""Gway command adapter for LCD operations."""

from __future__ import annotations

from .device import LCD
from .i2c import I2CLCD


def _address(value: str | int) -> int:
    return int(value, 0) if isinstance(value, str) else value


def _lcd(
    address: str | int = "0x27",
    bus: int = 1,
    columns: int = 16,
    rows: int = 2,
) -> LCD:
    return LCD(
        I2CLCD(
            address=_address(address),
            bus=bus,
            columns=columns,
            rows=rows,
        )
    )


def show(
    text: str,
    line: int = 1,
    address: str = "0x27",
    bus: int = 1,
    columns: int = 16,
    rows: int = 2,
) -> dict[str, object]:
    """Write text to one display line."""
    lcd = _lcd(address, bus, columns, rows)
    lcd.write_line(line, text)
    return {**lcd.status(), "line": line, "text": text}


def write(
    line1: str = "",
    line2: str = "",
    address: str = "0x27",
    bus: int = 1,
    columns: int = 16,
    rows: int = 2,
) -> dict[str, object]:
    """Write the first two display lines."""
    lcd = _lcd(address, bus, columns, rows)
    lcd.write(line1, line2)
    return {**lcd.status(), "line1": line1, "line2": line2}


def clear(
    address: str = "0x27",
    bus: int = 1,
    columns: int = 16,
    rows: int = 2,
) -> dict[str, object]:
    """Clear the display."""
    lcd = _lcd(address, bus, columns, rows)
    lcd.clear()
    return lcd.status()


def status(
    address: str = "0x27",
    bus: int = 1,
    columns: int = 16,
    rows: int = 2,
) -> dict[str, object]:
    """Initialize the display and return its configured identity."""
    return _lcd(address, bus, columns, rows).status()


def backlight(
    on: bool = True,
    address: str = "0x27",
    bus: int = 1,
    columns: int = 16,
    rows: int = 2,
) -> dict[str, object]:
    """Enable or disable the LCD backlight."""
    lcd = _lcd(address, bus, columns, rows)
    lcd.backlight(on)
    return {**lcd.status(), "backlight": on}


def detect(bus: int = 1) -> dict[str, object]:
    """Probe common character-LCD backpack addresses on an I2C bus."""
    try:
        from smbus2 import SMBus
    except ImportError as exc:
        raise RuntimeError(
            "I2C support requires the hardware extra: pip install 'gway-lcd[hardware]'"
        ) from exc

    found: list[str] = []
    with SMBus(bus) as i2c:
        for address in (0x27, 0x3E, 0x3F):
            try:
                i2c.read_byte(address)
            except OSError:
                continue
            found.append(f"0x{address:02x}")
    return {"bus": bus, "addresses": found}
