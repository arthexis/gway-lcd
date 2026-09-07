from gway_lcd import standby


def test_default_rotation_contains_status_stats_clock():
    screens, interval = standby.screens_from_config({})

    assert [screen.name for screen in screens] == ["status", "stats", "clock"]
    assert interval == 5.0


def test_cli_hi_lo_override_status_screen():
    screens, _interval = standby.screens_from_config({}, hi="Top", lo="Bottom")

    assert screens[0].name == "status"
    assert screens[0].hi == "Top"
    assert screens[0].lo == "Bottom"


def test_toml_screen_resolves_sigils(monkeypatch):
    monkeypatch.setenv("LCD_SITE", "GWAY-001")
    config = {
        "order": ["site"],
        "screens": {
            "site": {
                "hi": "[LCD_SITE|unknown]",
                "lo": "Ready",
            }
        },
    }

    screens, _interval = standby.screens_from_config(config)

    assert screens[0].hi == "GWAY-001"
    assert screens[0].lo == "Ready"


def test_low_legacy_name_maps_to_dynamic_uptime_screen():
    screens, _interval = standby.screens_from_config({"order": ["low"]})

    assert screens[0].name == "uptime"
    assert screens[0].kind == "dynamic"
