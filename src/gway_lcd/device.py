"""High-level character LCD device API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class LCDBackend(Protocol):
    """Backend contract used by :class:`LCD`."""

    driver: str
    address: int
    bus: int
    columns: int
    rows: int

    def clear(self) -> None: ...

    def write_line(self, line: int, text: str) -> None: ...

    def set_backlight(self, on: bool) -> None: ...


@dataclass
class LCD:
    """Small hardware-independent LCD facade."""

    backend: LCDBackend

    @property
    def columns(self) -> int:
        return self.backend.columns

    @property
    def rows(self) -> int:
        return self.backend.rows

    def clear(self) -> None:
        self.backend.clear()

    def write_line(self, line: int, text: str) -> None:
        if not 1 <= line <= self.rows:
            raise ValueError(f"line must be between 1 and {self.rows}")
        self.backend.write_line(line, text[: self.columns].ljust(self.columns))

    def write(self, line1: str = "", line2: str = "") -> None:
        self.write_line(1, line1)
        if self.rows >= 2:
            self.write_line(2, line2)

    def backlight(self, on: bool = True) -> None:
        self.backend.set_backlight(on)

    def status(self) -> dict[str, object]:
        return {
            "driver": self.backend.driver,
            "address": f"0x{self.backend.address:02x}",
            "bus": self.backend.bus,
            "columns": self.columns,
            "rows": self.rows,
        }
