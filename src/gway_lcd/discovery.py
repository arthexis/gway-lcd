"""I2C discovery and driver selection for supported Gway LCD hardware."""

from __future__ import annotations

import re
import subprocess

from .aip31068 import AiP31068LCD
from .i2c import I2CLCD

COMMON_ADDRESSES = (0x27, 0x3E, 0x3F)


def scan(bus: int = 1) -> set[int]:
    """Return detected common LCD addresses.

    Prefer i2cdetect because this matches the deployed Gway runner and works
    with the direct-I2C AiP31068 controller. Fall back to SMBus reads when
    i2c-tools is unavailable.
    """
    try:
        output = subprocess.check_output(
            ["i2cdetect", "-y", str(bus)],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        output = ""

    if output:
        found = {
            int(token, 16)
            for token in output.split()
            if re.fullmatch(r"[0-9a-fA-F]{2}", token)
        }
        return found.intersection(COMMON_ADDRESSES)

    try:
        from smbus2 import SMBus
    except ImportError as exc:
        raise RuntimeError(
            "I2C support requires the hardware extra: pip install 'gway-lcd[hardware]'"
        ) from exc

    found: set[int] = set()
    with SMBus(bus) as i2c:
        for address in COMMON_ADDRESSES:
            try:
                i2c.read_byte(address)
            except OSError:
                continue
            found.add(address)
    return found


def create_backend(
    *,
    driver: str = "auto",
    address: int | None = None,
    bus: int = 1,
    columns: int = 16,
    rows: int = 2,
):
    """Create the same LCD family selected by the deployed Gway runner."""
    preference = driver.lower().strip() or "auto"
    found = scan(bus) if preference == "auto" or address is None else set()

    if preference in {"aip", "aip31068", "waveshare"}:
        return AiP31068LCD(
            address=0x3E if address is None else address,
            bus=bus,
            columns=columns,
            rows=rows,
        )

    if preference in {"pcf", "pcf8574", "pcf8574a"}:
        selected = address
        if selected is None:
            selected = 0x3F if 0x3F in found else 0x3E if 0x3E in found else 0x27
        return I2CLCD(address=selected, bus=bus, columns=columns, rows=rows)

    if preference != "auto":
        raise ValueError(f"unsupported LCD driver: {driver}")

    if address is not None:
        if address == 0x3E:
            return AiP31068LCD(
                address=address, bus=bus, columns=columns, rows=rows
            )
        return I2CLCD(address=address, bus=bus, columns=columns, rows=rows)

    if 0x27 in found or 0x3F in found:
        selected = 0x3F if 0x3F in found else 0x27
        return I2CLCD(address=selected, bus=bus, columns=columns, rows=rows)
    if 0x3E in found:
        return AiP31068LCD(address=0x3E, bus=bus, columns=columns, rows=rows)

    # Preserve the historical Gway fallback when no address can be detected.
    return I2CLCD(address=0x27, bus=bus, columns=columns, rows=rows)
