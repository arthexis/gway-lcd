# gway-lcd

Gway-native control for character LCD displays on Raspberry Pi.

The package supports both LCD families already seen in deployed Gway boxes:

- AiP31068-compatible direct-I2C 16x2 displays at `0x3e` (the historical `waveshare` driver path).
- HD44780 displays behind PCF8574/PCF8574A I2C backpacks, commonly at `0x27` or `0x3f`.

The package keeps hardware access behind a small Python API and exposes composable commands through Gway.

## Install

For development and Raspberry Pi hardware access:

```console
python -m pip install -e ".[hardware,dev]"
```

The hardware extra installs `smbus2`. Importing `gway_lcd` itself does not require Raspberry Pi hardware or I2C support, so the core API can be tested on normal CI runners.

## Gway project

`gway.toml` exposes this package as the `lcd` project using the Python adapter.

```console
gway lcd detect
gway lcd status
gway lcd show --text "Ready"
gway lcd show --line 2 --text "Plug in"
gway lcd write --line1 "Ready" --line2 "Plug in"
gway lcd clear
```

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
- `write` writes the first two lines.
- `clear` clears the display.
- `backlight` toggles PCF8574 backpack backlight state.

Low-level controller operations remain internal to the hardware backends rather than becoming Gway commands.

## Compatibility with the deployed runner

The driver selection intentionally mirrors `gway-lcd-sound`'s standalone LCD1602 runner:

1. Explicit `aip`, `aip31068`, or `waveshare` selects AiP31068, defaulting to `0x3e`.
2. Explicit `pcf`, `pcf8574`, or `pcf8574a` selects the backpack backend.
3. Auto mode prefers PCF8574 when `0x27`/`0x3f` is present, otherwise selects AiP31068 for `0x3e`.
4. If no device can be detected, the historical fallback remains PCF8574 at `0x27`.

## CI

The repository uses the shared `arthexis/ci-base` `v1` workflow. Hardware selection is covered with fake backends, so normal CI does not require physical I2C devices.
