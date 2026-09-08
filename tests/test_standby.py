import pytest

from gway_lcd import standby


class FakeLCD:
    def __init__(self):
        self.frames = []

    def write(self, hi, lo):
        self.frames.append((hi, lo))


def test_default_rotation_uses_bundled_canonical_screens():
    screens, hold = standby.screens_from_config({})

    assert [screen.name for screen in screens] == [
        "identity",
        "network",
        "errors",
        "stats",
    ]
    assert hold == 10.0


def test_bundled_screen_templates_capture_canonical_layout():
    config = standby.load_config(None)
    screens = config["screens"]

    assert screens["identity"]["hi"] == "[device.hostname]"
    assert screens["identity"]["lo"] == "[arthexis.node-role|:-] [device.uptime]"
    assert screens["network"]["hi"] == "[network.ip:wlan0|:-]"
    assert screens["network"]["lo"] == "[network.ip:eth0|:-]"
    assert screens["errors"]["hi"] == (
        "E[device.errors] W[device.warnings] "
        "U[device.undervoltage:count] F[device.failed-units]"
    )
    assert screens["errors"]["lo"] == "[device.error-source|:-]"
    assert screens["stats"]["hi"] == (
        "M[device.memory:percent]% D[device.disk:free-percent]% "
        "C[device.cpu:percent]% [clock]"
    )
    assert screens["stats"]["lo"] == "[arthexis.version|:-] [arthexis.status||:FAIL]"


def test_named_screen_can_be_defined_from_cli_values():
    screens, _hold = standby.screens_from_config(
        {},
        screen="message",
        hi="Top",
        lo="Bottom",
        hold=15,
        priority=25,
    )

    assert len(screens) == 1
    assert screens[0].name == "message"
    assert screens[0].hi == "Top"
    assert screens[0].lo == "Bottom"
    assert screens[0].hold == 15
    assert screens[0].priority == 25


def test_user_screen_extends_bundled_screens():
    config = {
        "screens": {
            "site": {
                "hi": "Site",
                "lo": "Garage",
                "priority": 500,
            }
        }
    }

    screens, _hold = standby.screens_from_config(config, rotation="*")

    assert {screen.name for screen in screens} == {
        "identity",
        "network",
        "errors",
        "stats",
        "site",
    }


def test_user_screen_overrides_bundled_fields_by_name():
    config = {
        "screens": {
            "network": {
                "lo": "ETH custom",
                "hold": 20,
            }
        }
    }

    screens, _hold = standby.screens_from_config(config, screen="network")

    assert screens[0].hi == "[network.ip:wlan0|:-]"
    assert screens[0].lo == "ETH custom"
    assert screens[0].hold == 20


def test_manual_rotation_preserves_requested_order():
    screens, _hold = standby.screens_from_config(
        {},
        rotation="stats,identity,network,errors",
    )

    assert [screen.name for screen in screens] == [
        "stats",
        "identity",
        "network",
        "errors",
    ]


def test_user_rotation_can_replace_bundled_rotation():
    config = {"rotation": ["errors", "identity"]}

    screens, _hold = standby.screens_from_config(config)

    assert [screen.name for screen in screens] == ["errors", "identity"]


def test_screen_accepts_zero_or_more_project_prerequisites():
    config = {
        "screens": {
            "always": {"hi": "Always"},
            "net": {"hi": "Net", "requires": "network"},
            "node": {"hi": "Node", "requires": ["device", "arthexis"]},
        }
    }

    screens, _hold = standby.screens_from_config(config, rotation="always,net,node")

    assert screens[-3].requires == ()
    assert screens[-2].requires == ("network",)
    assert screens[-1].requires == ("device", "arthexis")


def test_sigils_resolve_at_render_time_with_one_context_per_frame(monkeypatch):
    calls = 0

    def fake_context():
        nonlocal calls
        calls += 1
        return {"value": calls}

    monkeypatch.setattr(standby, "gway_context", fake_context)
    lcd = FakeLCD()
    screens = [
        standby.Screen(name="one", hi="[value]", lo="[value]"),
        standby.Screen(name="two", hi="[value]", lo="[value]"),
    ]

    result = standby.run(lcd, screens, once=True)

    assert result["rendered"] == 2
    assert lcd.frames == [("1", "1"), ("2", "2")]
    assert calls == 2


def test_running_rotation_picks_up_new_project_without_restart(monkeypatch):
    calls = 0

    def fake_context():
        nonlocal calls
        calls += 1
        return {} if calls == 1 else {"network": {}}

    sleeps = 0

    def fake_sleep(_seconds):
        nonlocal sleeps
        sleeps += 1
        if sleeps == 2:
            raise StopIteration

    monkeypatch.setattr(standby, "gway_context", fake_context)
    monkeypatch.setattr(standby.time, "sleep", fake_sleep)
    lcd = FakeLCD()
    screens = [standby.Screen(name="net", hi="Network", requires=("network",))]

    with pytest.raises(StopIteration):
        standby.run(lcd, screens)

    assert lcd.frames == [("Network", "")]
    assert calls >= 2


def test_running_rotation_drops_removed_project_without_restart(monkeypatch):
    calls = 0

    def fake_context():
        nonlocal calls
        calls += 1
        return {"network": {}} if calls == 1 else {}

    sleeps = 0

    def fake_sleep(_seconds):
        nonlocal sleeps
        sleeps += 1
        if sleeps == 2:
            raise StopIteration

    monkeypatch.setattr(standby, "gway_context", fake_context)
    monkeypatch.setattr(standby.time, "sleep", fake_sleep)
    lcd = FakeLCD()
    screens = [standby.Screen(name="net", hi="Network", requires=("network",))]

    with pytest.raises(StopIteration):
        standby.run(lcd, screens)

    assert lcd.frames == [("Network", "")]
    assert calls >= 2


def test_low_legacy_name_maps_to_dynamic_uptime_screen():
    screen = standby.builtin_screen("low")

    assert screen.name == "uptime"
    assert screen.kind == "dynamic"
