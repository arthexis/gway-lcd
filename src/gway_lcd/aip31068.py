"""AiP31068 direct-I2C character LCD backend used by deployed Gway boxes."""

from __future__ import annotations

import time


class AiP31068LCD:
    """16x2 AiP31068-compatible LCD at the common Waveshare address 0x3E."""

    driver = "aip31068"

    def __init__(
        self,
        address: int = 0x3E,
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
        self._bus = SMBus(bus)
        self._initialize()

    def _command(self, value: int) -> None:
        self._bus.write_byte_data(self.address, 0x80, value & 0xFF)
        time.sleep(0.002)

    def _data(self, value: int) -> None:
        self._bus.write_byte_data(self.address, 0x40, value & 0xFF)
        time.sleep(0.001)

    def _initialize(self) -> None:
        time.sleep(0.05)
        self._command(0x28)
        time.sleep(0.005)
        self._command(0x28)
        time.sleep(0.005)
        self._command(0x28)
        self._command(0x08)
        self.clear()
        self._command(0x06)
        self._command(0x0C)

    def clear(self) -> None:
        self._command(0x01)
        time.sleep(0.005)

    def write_line(self, line: int, text: str) -> None:
        offsets = (0x00, 0x40, 0x14, 0x54)
        if not 1 <= line <= min(self.rows, len(offsets)):
            raise ValueError(f"line must be between 1 and {self.rows}")
        self._command(0x80 | offsets[line - 1])
        for char in text[: self.columns].ljust(self.columns):
            self._data(ord(char))

    def set_backlight(self, on: bool) -> None:
        raise NotImplementedError(
            "AiP31068 direct-I2C displays do not expose backpack backlight control"
        )

    def close(self) -> None:
        self._bus.close()
