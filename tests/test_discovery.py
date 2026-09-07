from gway_lcd import discovery


class FakePCF:
    driver = "pcf8574"

    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeAiP:
    driver = "aip31068"

    def __init__(self, **kwargs):
        self.kwargs = kwargs


def test_auto_selects_aip31068_for_deployed_0x3e_screen(monkeypatch):
    monkeypatch.setattr(discovery, "scan", lambda bus=1: {0x3E})
    monkeypatch.setattr(discovery, "AiP31068LCD", FakeAiP)
    monkeypatch.setattr(discovery, "I2CLCD", FakePCF)

    backend = discovery.create_backend()

    assert isinstance(backend, FakeAiP)
    assert backend.kwargs["address"] == 0x3E


def test_auto_prefers_pcf_backpack_when_0x27_is_present(monkeypatch):
    monkeypatch.setattr(discovery, "scan", lambda bus=1: {0x27, 0x3E})
    monkeypatch.setattr(discovery, "AiP31068LCD", FakeAiP)
    monkeypatch.setattr(discovery, "I2CLCD", FakePCF)

    backend = discovery.create_backend()

    assert isinstance(backend, FakePCF)
    assert backend.kwargs["address"] == 0x27


def test_auto_prefers_0x3f_pcf_when_present(monkeypatch):
    monkeypatch.setattr(discovery, "scan", lambda bus=1: {0x3F})
    monkeypatch.setattr(discovery, "AiP31068LCD", FakeAiP)
    monkeypatch.setattr(discovery, "I2CLCD", FakePCF)

    backend = discovery.create_backend()

    assert isinstance(backend, FakePCF)
    assert backend.kwargs["address"] == 0x3F


def test_waveshare_alias_selects_aip31068(monkeypatch):
    monkeypatch.setattr(discovery, "scan", lambda bus=1: set())
    monkeypatch.setattr(discovery, "AiP31068LCD", FakeAiP)

    backend = discovery.create_backend(driver="waveshare")

    assert isinstance(backend, FakeAiP)
    assert backend.kwargs["address"] == 0x3E


def test_explicit_0x3e_uses_aip31068_in_auto_mode(monkeypatch):
    monkeypatch.setattr(discovery, "scan", lambda bus=1: set())
    monkeypatch.setattr(discovery, "AiP31068LCD", FakeAiP)

    backend = discovery.create_backend(address=0x3E)

    assert isinstance(backend, FakeAiP)
