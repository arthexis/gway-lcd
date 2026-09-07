"""Configurable standby screen rotation for Gway LCD displays."""

from __future__ import annotations

import os
import socket
import time
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sigils import Sigil


@dataclass(frozen=True)
class Screen:
    """One two-line standby frame."""

    name: str
    hi: str = ""
    lo: str = ""
    kind: str = "static"


def _uptime() -> str:
    try:
        seconds = int(float(Path("/proc/uptime").read_text().split()[0]))
    except (OSError, ValueError, IndexError):
        return "?"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d{hours}h{minutes}m"
    if hours:
        return f"{hours}h{minutes}m"
    return f"{minutes}m"


def _local_now() -> datetime:
    return datetime.now(UTC).astimezone()


def _runtime_context() -> dict[str, object]:
    """Values available to sigils embedded in standby TOML strings."""
    hostname = socket.gethostname()
    return {
        **os.environ,
        "hostname": hostname,
        "host": hostname,
        "uptime": _uptime(),
        "now": _local_now().isoformat(timespec="seconds"),
    }


def resolve_text(value: object, context: dict[str, object] | None = None) -> str:
    """Resolve Gway-style sigils in one configured string."""
    return Sigil("" if value is None else str(value)).solve(
        context or _runtime_context()
    )


def builtin_screen(name: str) -> Screen:
    """Return a dynamic standby frame matching the useful legacy screens."""
    now = _local_now()
    if name in {"low", "uptime"}:
        return Screen(
            name="uptime",
            hi=f"UP {_uptime()}",
            lo=now.strftime("%a %H:%M:%S"),
            kind="dynamic",
        )
    if name == "stats":
        load = " ".join(f"{value:.2f}" for value in os.getloadavg()[:2])
        return Screen(
            name="stats",
            hi=f"LOAD {load}",
            lo=f"UP {_uptime()}",
            kind="dynamic",
        )
    if name == "clock":
        return Screen(
            name="clock",
            hi=now.strftime("%p %I:%M").replace(" 0", " "),
            lo=now.strftime("%Y-%m-%d %a"),
            kind="dynamic",
        )
    raise KeyError(name)


def load_config(path: str | Path | None) -> dict[str, object]:
    if path is None:
        return {}
    config_path = Path(path).expanduser()
    with config_path.open("rb") as handle:
        data = tomllib.load(handle)
    standby = data.get("standby", {})
    if not isinstance(standby, dict):
        raise TypeError("[standby] must be a TOML table")
    return standby


def screens_from_config(
    config: dict[str, object],
    *,
    hi: str = "",
    lo: str = "",
    order: str | None = None,
) -> tuple[list[Screen], float]:
    """Build a rotation from TOML plus optional CLI overrides."""
    interval = float(config.get("interval", 5.0))
    configured = config.get("screens", {})
    screen_map = configured if isinstance(configured, dict) else {}

    raw_order: object = order or config.get("order", ["status", "stats", "clock"])
    if isinstance(raw_order, str):
        names = [item.strip() for item in raw_order.split(",") if item.strip()]
    elif isinstance(raw_order, list):
        names = [str(item).strip() for item in raw_order if str(item).strip()]
    else:
        raise TypeError("standby order must be a list or comma-separated string")

    cli_frame = Screen("status", hi=hi, lo=lo) if hi or lo else None
    screens: list[Screen] = []
    context = _runtime_context()
    for name in names:
        if name == "status" and cli_frame is not None:
            screens.append(cli_frame)
            continue
        entry = screen_map.get(name)
        if isinstance(entry, dict):
            screens.append(
                Screen(
                    name=name,
                    hi=resolve_text(entry.get("hi", entry.get("high", "")), context),
                    lo=resolve_text(entry.get("lo", entry.get("low", "")), context),
                )
            )
            continue
        try:
            screens.append(builtin_screen(name))
        except KeyError:
            if name == "status":
                screens.append(
                    Screen(
                        name="status",
                        hi=resolve_text("[hostname]", context),
                        lo="Ready",
                    )
                )
            else:
                raise ValueError(f"unknown standby screen: {name}") from None
    return screens, interval


def run(
    lcd,
    screens: list[Screen],
    *,
    interval: float = 5.0,
    once: bool = False,
) -> dict[str, object]:
    """Render standby frames, refreshing dynamic screens each cycle."""
    if not screens:
        raise ValueError("standby requires at least one screen")

    rendered = 0
    while True:
        for configured in screens:
            frame = (
                builtin_screen(configured.name)
                if configured.kind == "dynamic"
                else configured
            )
            lcd.write(frame.hi, frame.lo)
            rendered += 1
            if once:
                continue
            time.sleep(interval)
        if once:
            break
    return {"screens": [screen.name for screen in screens], "rendered": rendered}
