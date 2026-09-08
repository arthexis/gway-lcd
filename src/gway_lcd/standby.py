"""Configurable standby screen rotation for Gway LCD displays."""

from __future__ import annotations

import os
import socket
import time
import tomllib
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from sigils import Sigil

DEFAULT_HOLD = 10.0


@dataclass(frozen=True)
class Screen:
    """One named two-line standby frame."""

    name: str
    hi: str = ""
    lo: str = ""
    kind: str = "static"
    hold: float = DEFAULT_HOLD
    priority: int = 100


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
    hostname = socket.gethostname()
    return {
        **os.environ,
        "hostname": hostname,
        "host": hostname,
        "uptime": _uptime(),
        "now": _local_now().isoformat(timespec="seconds"),
    }


def resolve_text(value: object, context: dict[str, object] | None = None) -> str:
    return Sigil("" if value is None else str(value)).solve(
        context or _runtime_context()
    )


def builtin_screen(name: str) -> Screen:
    """Return one dynamic built-in screen."""
    now = _local_now()
    if name in {"low", "uptime"}:
        return Screen(
            name="uptime",
            hi=f"UP {_uptime()}",
            lo=now.strftime("%a %H:%M:%S"),
            kind="dynamic",
            priority=200,
        )
    if name == "stats":
        load = " ".join(f"{value:.2f}" for value in os.getloadavg()[:2])
        return Screen(
            name="stats",
            hi=f"LOAD {load}",
            lo=f"UP {_uptime()}",
            kind="dynamic",
            priority=300,
        )
    if name == "clock":
        return Screen(
            name="clock",
            hi=now.strftime("%p %I:%M").replace(" 0", " "),
            lo=now.strftime("%Y-%m-%d %a"),
            kind="dynamic",
            priority=400,
        )
    if name == "status":
        return Screen(
            name="status",
            hi=resolve_text("[hostname]"),
            lo="Ready",
            priority=100,
        )
    raise KeyError(name)


def load_config(path: str | Path | None) -> dict[str, object]:
    if path is None:
        return {}
    with Path(path).expanduser().open("rb") as handle:
        data = tomllib.load(handle)
    standby = data.get("standby", {})
    if not isinstance(standby, dict):
        raise TypeError("[standby] must be a TOML table")
    return standby


def _configured_screen(name: str, entry: dict[str, object]) -> Screen:
    context = _runtime_context()
    return Screen(
        name=name,
        hi=resolve_text(entry.get("hi", entry.get("high", "")), context),
        lo=resolve_text(entry.get("lo", entry.get("low", "")), context),
        hold=float(entry.get("hold", DEFAULT_HOLD)),
        priority=int(entry.get("priority", 100)),
    )


def _screen_map(config: dict[str, object]) -> dict[str, Screen]:
    result = {name: builtin_screen(name) for name in ("status", "stats", "clock")}
    configured = config.get("screens", {})
    if isinstance(configured, dict):
        for name, entry in configured.items():
            if isinstance(entry, dict):
                result[str(name)] = _configured_screen(str(name), entry)
    return result


def _rotation_names(rotation: str | None, screens: dict[str, Screen]) -> list[str]:
    if rotation is None:
        return [
            screen.name
            for screen in sorted(screens.values(), key=lambda item: item.priority)
        ]
    if rotation.strip() == "*":
        return list(screens)
    return [item for item in rotation.replace(",", " ").split() if item]


def screens_from_config(
    config: dict[str, object],
    *,
    screen: str | None = None,
    hi: str = "",
    lo: str = "",
    rotation: str | None = None,
    order: str | None = None,
    hold: float = DEFAULT_HOLD,
    priority: int = 100,
) -> tuple[list[Screen], float]:
    """Build named screens and select a rotation or one standalone screen."""
    screens = _screen_map(config)
    default_hold = float(config.get("hold", config.get("interval", DEFAULT_HOLD)))

    if screen is not None and (hi or lo):
        screens[screen] = Screen(
            name=screen,
            hi=hi,
            lo=lo,
            hold=hold,
            priority=priority,
        )

    if screen is not None and rotation is None and order is None:
        if screen not in screens:
            raise ValueError(f"unknown standby screen: {screen}")
        return [screens[screen]], default_hold

    selected_rotation = rotation if rotation is not None else order
    names = _rotation_names(selected_rotation, screens)
    selected: list[Screen] = []
    for name in names:
        if name not in screens:
            raise ValueError(f"unknown standby screen: {name}")
        selected.append(screens[name])
    return selected, default_hold


def run(
    lcd,
    screens: list[Screen],
    *,
    default_hold: float = DEFAULT_HOLD,
    once: bool = False,
) -> dict[str, object]:
    """Render named screens, respecting each screen's hold time."""
    if not screens:
        raise ValueError("standby requires at least one screen")

    rendered = 0
    while True:
        for configured in screens:
            frame = builtin_screen(configured.name) if configured.kind == "dynamic" else configured
            if configured.kind == "dynamic":
                frame = replace(
                    frame,
                    hold=configured.hold,
                    priority=configured.priority,
                )
            lcd.write(frame.hi, frame.lo)
            rendered += 1
            if not once:
                time.sleep(frame.hold if frame.hold > 0 else default_hold)
        if once:
            break
    return {
        "screens": [screen.name for screen in screens],
        "rendered": rendered,
    }
