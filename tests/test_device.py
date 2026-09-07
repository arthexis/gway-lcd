from gway_lcd import LCD


class FakeBackend:
    address = 0x27
    bus = 1
    columns = 16
    rows = 2

    def __init__(self):
        self.lines = {}
        self.cleared = False
        self.backlight = True

    def clear(self):
        self.cleared = True

    def write_line(self, line, text):
        self.lines[line] = text

    def set_backlight(self, on):
        self.backlight = on


def test_write_line_is_padded_and_truncated():
    backend = FakeBackend()
    lcd = LCD(backend)

    lcd.write_line(1, "hello")
    lcd.write_line(2, "0123456789abcdefgh")

    assert backend.lines[1] == "hello           "
    assert backend.lines[2] == "0123456789abcdef"


def test_write_updates_both_lines():
    backend = FakeBackend()
    lcd = LCD(backend)

    lcd.write("ready", "plug in")

    assert backend.lines[1] == "ready           "
    assert backend.lines[2] == "plug in         "


def test_clear_and_backlight_delegate_to_backend():
    backend = FakeBackend()
    lcd = LCD(backend)

    lcd.clear()
    lcd.backlight(False)

    assert backend.cleared is True
    assert backend.backlight is False


def test_status_is_serializable_configuration():
    lcd = LCD(FakeBackend())

    assert lcd.status() == {
        "address": "0x27",
        "bus": 1,
        "columns": 16,
        "rows": 2,
    }
