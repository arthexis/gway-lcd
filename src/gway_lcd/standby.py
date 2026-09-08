"""Configurable standby screen rotation for Gway LCD displays."""

from __future__ import annotations

import os
import socket
import time
import tomllib
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path

from sigils import Sigil

try:
    from gway import gway_context
except ImportError:  # GWAY releases before gway_context remain usable.
    gway_context = None

DEFAULT_HOLD = 10.0
BUNDLED_CONFIG = "standby.toml"


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
    now = _local_now()
    context: dict[str, object] = {
        **os.environ,
        "hostname": hostname,
        "host": hostname,
        "uptime": _uptime(),
        "now": now.isoformat(timespec="seconds"),
        "clock": now.strftime("%H:%M"),
    }
    if gway_context is not None:
        context.update(gway_context())
    return context


def resolve_text(value: object, context: dict[str, object] | None = None) -> str:
    return Sigil("" if value is None else str(value)).solve(
        context or _runtime_context()
    )


def builtin_screen(name: str) -> Screen:
    """Return one compatibility built-in screen."""
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
            hi="[hostname]",
            lo="Ready",
            priority=100,
        )
    raise KeyError(name)


def _bundled_config() -> dict[str, object]:
    resource = files("gway_lcd").joinpath(BUNDLED_CONFIG)
    data = tomllib.loads(resource.read_text(encoding="utf-8"))
    standby = data.get("standby", {})
    if not isinstance(standby, dict):
        raise TypeError("bundled [standby] must be a TOML table")
    return standby


def _merge_config(
    base: dict[str, object], override: dict[str, object]
) -> dict[str, object]:
    merged = dict(base)
    base_screens = base.get("screens", {})
    override_screens = override.get("screens", {})
    if isinstance(base_screens, dict):
        screens = {
            str(name): dict(entry) if isinstance(entry, dict) else entry
            for name, entry in base_screens.items()
        }
    else:
        screens = {}
    if isinstance(override_screens, dict):
        for name, entry in override_screens.items():
            key = str(name)
            if isinstance(entry, dict) and isinstance(screens.get(key), dict):
                screens[key] = {**screens[key], **entry}
            else:
                screens[key] = entry
    merged.update({key: value for key, value in override.items() if key != "screens"})
    merged["screens"] = screens
    return merged


def load_config(path: str | Path | None) -> dict[str, object]:
    """Load bundled standby defaults and merge optional user configuration."""
    bundled = _bundled_config()
    if path is None:
        return bundled
    with Path(path).expanduser().open("rb") as handle:
        data = tomllib.load(handle)
    standby = data.get("standby", {})
    if not isinstance(standby, dict):
        raise TypeError("[standby] must be a TOML table")
    return _merge_config(bundled, standby)


def _configured_screen(name: str, entry: dict[str, object]) -> Screen:
    has_text = any(key in entry for key in ("hi", "high", "lo", "low"))
    if not has_text and name in {"status", "stats", "clock"}:
        base = builtin_screen(name)
        return replace(
            base,
            hold=float(entry.get("hold", base.hold)),
            priority=int(entry.get("priority", base.priority)),
        )

    return Screen(
        name=name,
        hi=str(entry.get("hi", entry.get("high", ""))),
        lo=str(entry.get("lo", entry.get("low", ""))),
        hold=float(entry.get("hold", DEFAULT_HOLD)),
        priority=int(entry.get("priority", 100)),
    )


def _screen_map(config: dict[str, object]) -> dict[str, Screen]:
    result: dict[str, Screen] = {}
    configured = config.get("screens", {})
    if isinstance(configured, dict):
        for name, entry in configured.items():
            if isinstance(entry, dict):
                result[str(name)] = _configured_screen(str(name), entry)
    return result


def _rotation_names(
    rotation: str | list[str] | tuple[str, ...] | None,
    screens: dict[str, Screen],
) -> list[str]:
    if rotation is None:
        return [
            screen.name
            for screen in sorted(screens.values(), key=lambda item: item.priority)
        ]
    if isinstance(rotation, (list, tuple)):
        return [str(item) for item in rotation]
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
    """Build bundled/user screens and select a rotation or standalone screen."""
    effective = _merge_config(_bundled_config(), config)
    screens = _screen_map(effective)
    default_hold = float(effective.get("hold", effective.get("interval", DEFAULT_HOLD)))

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

    selected_rotation: str | list[str] | tuple[str, ...] | None
    if rotation is not None:
        selected_rotation = rotation
    elif order is not None:
        selected_rotation = order
    else:
        bundled_rotation = effective.get("rotation")
        selected_rotation = (
            bundled_rotation
            if isinstance(bundled_rotation, (str, list, tuple))
            else None
        )
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
    """Render named screens with one fresh GWAY/Sigil context per frame."""
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
            if configured.kind == "dynamic":
                frame = replace(
                    frame,
                    hold=configured.hold,
                    priority=configured.priority,
                )
            context = _runtime_context()
            lcd.write(
                resolve_text(frame.hi, context),
                resolve_text(frame.lo, context),
            )
            rendered += 1
            if not once:
                time.sleep(frame.hold if frame.hold > 0 else default_hold)
        if once:
            break
    return {
        "screens": [screen.name for screen in screens],
        "rendered": rendered,
    }
