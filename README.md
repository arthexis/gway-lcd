# gway-lcd

Gway-native control for character LCD displays, starting with HD44780-compatible I2C backpacks on Raspberry Pi.

The package keeps hardware access behind a small Python API and exposes composable commands through Gway.

## Install

For development:

```console
python -m pip install -e ".[hardware,dev]"
```

The hardware extra currently installs `smbus2`. Importing `gway_lcd` itself does not require Raspberry Pi hardware or I2C support, so the core API can be tested on normal CI runners.

## Gway project

`gway.toml` exposes this package as the `lcd` project using the Python adapter.

```console
gway lcd detect
gway lcd status
gway lcd show --text "Ready"
gway lcd show --line 2 --text "Plug in"
gway lcd write --line1 "Ready" --line2 "Plug in"
gway lcd clear
gway lcd backlight --no-on
```

Defaults are bus `1`, address `0x27`, and a 16x2 display. Address, bus, columns, and rows are regular command arguments and can therefore be supplied by Gway context/sigils in composed workflows.

Example:

```console
gway lcd detect - lcd show --address "[address|0x27]" --text "Ready"
```

## Python API

The public `LCD` facade depends only on a backend protocol. This keeps orchestration separate from the physical transport and allows fake backends in tests.

```python
from gway_lcd import LCD
from gway_lcd.i2c import I2CLCD

lcd = LCD(I2CLCD(address=0x27, bus=1, columns=16, rows=2))
lcd.write("Ready", "Plug in")
```

## Initial command surface

- `detect` probes common backpack addresses (`0x27`, `0x3e`, `0x3f`).
- `status` returns configured device identity.
- `show` writes one line.
- `write` writes the first two lines.
- `clear` clears the display.
- `backlight` toggles the backpack backlight.

Low-level HD44780 operations remain internal to the I2C backend rather than becoming Gway commands.

## CI

The repository uses the shared `arthexis/ci-base` `v1` workflow. The central baseline currently runs quality/build checks on the shared default Python version and tests across the centrally managed Python test matrix.
