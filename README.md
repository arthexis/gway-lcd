# gway-lcd

Gway-native control for character LCD displays on Raspberry Pi.

The package supports both LCD families already seen in deployed Gway boxes:

- AiP31068-compatible direct-I2C 16x2 displays at `0x3e` (the historical `waveshare` driver path).
- HD44780 displays behind PCF8574/PCF8574A I2C backpacks, commonly at `0x27` or `0x3f`.

The package keeps hardware access behind a small Python API and exposes composable commands through Gway.

## Install

For normal Gway installation:

```console
sudo gway install lcd
```

`smbus2` and `gway-sigils` are normal package dependencies, so no extra install flag is required for Raspberry Pi I2C access or standby templates.

For development:

```console
python -m pip install -e ".[dev]"
```

## Gway project

`gway.toml` exposes this package as the `lcd` project using the Python adapter.

```console
gway lcd detect
gway lcd status
gway lcd show --text "Ready"
gway lcd show --line 2 --text "Plug in"
gway lcd write --hi "Ready" --lo "Plug in"
gway lcd write --high "Ready" --low "Plug in"
gway lcd clear
```

`hi`/`high` is the physical top row and `lo`/`low` is the physical bottom row.

By default the driver and address are auto-detected on I2C bus `1`, using the same selection rules as the deployed Gway LCD runner. A detected `0x3e` device selects AiP31068; `0x27` or `0x3f` selects the PCF8574 backend. The historical driver aliases are also accepted:

```console
gway lcd status --driver waveshare
gway lcd status --driver aip31068
gway lcd status --driver pcf8574
gway lcd show --driver waveshare --address 0x3e --text "Ready"
```

Backlight control is a PCF8574-backpack feature and is not exposed by the direct-I2C AiP31068 controller:

```console
gway lcd backlight --no-on --driver pcf8574
```

Address, bus, columns, rows, and driver are regular command arguments and can therefore be supplied by Gway context/sigils in composed workflows.

## Standby mode

`standby` replaces the useful rotating standby behavior from `gway-lcd-sound` with a configurable Gway-native loop. The default rotation is `status`, `stats`, `clock`; `stats`, `clock`, and the legacy `low`/`uptime` name are dynamic and refresh every cycle.

Run the defaults:

```console
gway lcd standby
```

Override the status frame and rotation from the CLI:

```console
gway lcd standby \
  --hi "[hostname|Gway]" \
  --lo "[state|Ready]" \
  --order status,stats,clock \
  --interval 5
```

CLI values are resolved by Gway before dispatch, so ordinary lazy/eager sigils work as usual.

A TOML file can define named standby screens:

```toml
[standby]
interval = 5
order = ["status", "network", "stats", "clock"]

[standby.screens.status]
hi = "[hostname|Gway]"
lo = "Ready"

[standby.screens.network]
hi = "ETH [eth0_ip|offline]"
lo = "CSMS [csms_status|idle]"
```

Use it with:

```console
gway lcd standby --config ~/.config/gway/lcd.toml
```

TOML string values are also passed through `gway-sigils`. The standby runtime supplies environment variables plus `hostname`, `host`, `uptime`, and `now`; unresolved values can therefore use normal Sigil fallbacks.

`config/lcd.toml` contains a starter configuration. `config/systemd/gway-lcd-standby.service` is a user-service unit that runs:

```console
/opt/gway/venv/bin/gway lcd standby --config %h/.config/gway/lcd.toml
```

For one-pass testing without leaving a foreground loop running:

```console
gway lcd standby --once
```

## Python API

The public `LCD` facade depends only on a backend protocol. This keeps orchestration separate from the physical transport and allows fake backends in tests.

```python
from gway_lcd import LCD
from gway_lcd.discovery import create_backend

lcd = LCD(create_backend())
lcd.write("Ready", "Plug in")
```

Explicit backend construction is also available through `gway_lcd.aip31068.AiP31068LCD` and `gway_lcd.i2c.I2CLCD`.

## Command surface

- `detect` reports supported devices and their inferred drivers.
- `status` auto-selects and initializes the display, then returns device identity.
- `show` writes one line.
- `write` writes the high/top and low/bottom rows.
- `standby` runs a configurable rotating standby display.
- `clear` clears the display.
- `backlight` toggles PCF8574 backpack backlight state.

Low-level controller operations remain internal to the hardware backends rather than becoming Gway commands.

## Compatibility with the deployed runner

The driver selection intentionally mirrors `gway-lcd-sound`'s standalone LCD1602 runner:

1. Explicit `aip`, `aip31068`, or `waveshare` selects AiP31068, defaulting to `0x3e`.
2. Explicit `pcf`, `pcf8574`, or `pcf8574a` selects the backpack backend.
3. Auto mode prefers PCF8574 when `0x27`/`0x3f` is present, otherwise selects AiP31068 for `0x3e`.
4. If no device can be detected, the historical fallback remains PCF8574 at `0x27`.

The legacy runner's useful generated standby frames are retained without carrying forward its ambiguous channel names: physical rows are always `hi/high` and `lo/low`, while standby frames have independent names such as `status`, `stats`, and `clock`.

## CI

The repository uses the shared `arthexis/ci-base` `v1` workflow. Hardware selection and standby configuration are covered with fake backends, so normal CI does not require physical I2C devices.
