from scripts.utils import config_loader as cl


def test_load_config_with_drivers_handles_non_dict(monkeypatch):
    monkeypatch.setattr(cl, "load_config", lambda: "not-a-dict")
    cfg, drv = cl.load_config_with_drivers()
    assert cfg == {}
    assert drv == {}


def test_load_qa_config_returns_targets(monkeypatch):
    monkeypatch.setattr(
        cl,
        "load_config",
        lambda: {"drivers": {"enabled": True}, "project": {"targets": {"backend": "be"}}},
    )
    cfg, drv, targets = cl.load_qa_config()
    assert drv == {"enabled": True}
    assert targets == {"backend": "be"}


def test_normalize_bool_variants():
    assert cl.normalize_bool(None, default=True) is True
    assert cl.normalize_bool("TrUe") is True
    assert cl.normalize_bool("no") is False
    assert cl.normalize_bool(0) is False
