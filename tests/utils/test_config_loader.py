from __future__ import annotations

from typing import Any, Dict

import pytest

from scripts.utils import config_loader


def test_load_config_base_uses_default_when_exception(monkeypatch):
    monkeypatch.setattr(config_loader, "load_config", lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    cfg = config_loader.load_config_base()
    assert cfg == {}


def test_load_config_base_returns_mapping(monkeypatch):
    sample = {"drivers": {"enabled": True}}
    monkeypatch.setattr(config_loader, "load_config", lambda: sample)
    cfg = config_loader.load_config_base()
    assert cfg is sample


def test_load_config_with_drivers(monkeypatch):
    sample = {"drivers": {"enabled": False, "embedded": {"run_build": True}}}
    monkeypatch.setattr(config_loader, "load_config", lambda: sample)
    cfg, drv_cfg = config_loader.load_config_with_drivers()
    assert cfg is sample
    assert drv_cfg == sample["drivers"]


def test_load_qa_config(monkeypatch):
    sample = {"drivers": {"enabled": True}, "project": {"targets": {"backend": "fastapi"}}}
    monkeypatch.setattr(config_loader, "load_config", lambda: sample)
    cfg, drv_cfg, targets = config_loader.load_qa_config()
    assert cfg is sample
    assert drv_cfg == sample["drivers"]
    assert targets == {"backend": "fastapi"}


@pytest.mark.parametrize(
    "value,default,expected",
    [
        (None, False, False),
        (None, True, True),
        (True, False, True),
        ("true", False, True),
        ("Yes", False, True),
        ("0", True, False),
        (0, True, False),
        ("off", True, False),
    ],
)
def test_normalize_bool(value: Any, default: bool, expected: bool):
    assert config_loader.normalize_bool(value, default) is expected
