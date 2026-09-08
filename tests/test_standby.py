from gway_lcd import standby


def test_default_rotation_uses_priority_order():
    screens, hold = standby.screens_from_config({})

    assert [screen.name for screen in screens] == ["status", "stats", "clock"]
    assert hold == 10.0


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


def test_standalone_named_screen_loads_from_config():
    config = {
        "screens": {
            "network": {
                "hi": "Online",
                "lo": "10.42.0.1",
                "hold": 20,
                "priority": 50,
            }
        }
    }

    screens, _hold = standby.screens_from_config(config, screen="network")

    assert [screen.name for screen in screens] == ["network"]
    assert screens[0].hold == 20


def test_manual_rotation_preserves_requested_order():
    config = {
        "screens": {
            "network": {"hi": "Network", "priority": 50},
        }
    }

    screens, _hold = standby.screens_from_config(
        config,
        rotation="clock,network,status",
    )

    assert [screen.name for screen in screens] == ["clock", "network", "status"]


def test_star_rotation_includes_all_screens():
    config = {"screens": {"network": {"hi": "Network"}}}

    screens, _hold = standby.screens_from_config(config, rotation="*")

    assert {screen.name for screen in screens} == {"status", "stats", "clock", "network"}


def test_priority_orders_configured_screens_when_rotation_is_implicit():
    config = {
        "screens": {
            "network": {"hi": "Network", "priority": 50},
            "slow": {"hi": "Slow", "priority": 350},
        }
    }

    screens, _hold = standby.screens_from_config(config)

    assert [screen.name for screen in screens] == [
        "network",
        "status",
        "stats",
        "slow",
        "clock",
    ]


def test_toml_screen_resolves_sigils(monkeypatch):
    monkeypatch.setenv("LCD_SITE", "GWAY-001")
    config = {
        "screens": {
            "site": {
                "hi": "[LCD_SITE]",
                "lo": "Ready",
                "priority": 10,
            }
        },
    }

    screens, _hold = standby.screens_from_config(config, screen="site")

    assert screens[0].hi == "GWAY-001"
    assert screens[0].lo == "Ready"


def test_low_legacy_name_maps_to_dynamic_uptime_screen():
    screen = standby.builtin_screen("low")

    assert screen.name == "uptime"
    assert screen.kind == "dynamic"
