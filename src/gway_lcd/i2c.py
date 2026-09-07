"""HD44780 I2C backpack backend."""

from __future__ import annotations

import time


class I2CLCD:
    """Minimal PCF8574-style HD44780 backend."""

    driver = "pcf8574"
    ENABLE = 0x04
    BACKLIGHT = 0x08
    DATA = 0x01

    def __init__(
        self,
        address: int = 0x27,
        bus: int = 1,
        columns: int = 16,
        rows: int = 2,
    ) -> None:
        try:
            from smbus2 import SMBus
        except ImportError as exc:
            raise RuntimeError(
                "I2C support requires smbus2; reinstall gway-lcd with 'gway install lcd'"
            ) from exc

        self.address = address
        self.bus = bus
        self.columns = columns
        self.rows = rows
        self._backlight = self.BACKLIGHT
        self._bus = SMBus(bus)
        self._initialize()

    def _write_raw(self, value: int) -> None:
        self._bus.write_byte(self.address, value | self._backlight)

    def _pulse(self, value: int) -> None:
        self._write_raw(value | self.ENABLE)
        time.sleep(0.0005)
        self._write_raw(value & ~self.ENABLE)
        time.sleep(0.0001)

    def _nibble(self, value: int, mode: int = 0) -> None:
        payload = (value & 0xF0) | mode
        self._write_raw(payload)
        self._pulse(payload)

    def _send(self, value: int, mode: int = 0) -> None:
        self._nibble(value & 0xF0, mode)
        self._nibble((value << 4) & 0xF0, mode)

    def _initialize(self) -> None:
        time.sleep(0.05)
        for value in (0x30, 0x30, 0x30, 0x20):
            self._nibble(value)
            time.sleep(0.005)
        self._send(0x28)
        self._send(0x0C)
        self._send(0x06)
        self.clear()

    def clear(self) -> None:
        self._send(0x01)
        time.sleep(0.002)

    def write_line(self, line: int, text: str) -> None:
        offsets = (0x00, 0x40, 0x14, 0x54)
        if not 1 <= line <= min(self.rows, len(offsets)):
            raise ValueError(f"line must be between 1 and {self.rows}")
        self._send(0x80 | offsets[line - 1])
        for char in text:
            self._send(ord(char), self.DATA)

    def set_backlight(self, on: bool) -> None:
        self._backlight = self.BACKLIGHT if on else 0
        self._write_raw(0)

    def close(self) -> None:
        self._bus.close()
