import sys
import types

from scripts.utils.db_context import get_db_context_or_default


def test_returns_current_context_when_present(monkeypatch):
    dummy_ctx = object()
    fake_db = types.SimpleNamespace(
        get_current_context=lambda: dummy_ctx,
        dual_write=types.SimpleNamespace(get_or_create_adhoc_context=lambda: "adhoc"),
    )
    monkeypatch.setitem(sys.modules, "src.db", fake_db)
    assert get_db_context_or_default() is dummy_ctx


def test_creates_adhoc_when_no_context(monkeypatch):
    fake_db = types.SimpleNamespace(
        get_current_context=lambda: None,
        dual_write=types.SimpleNamespace(get_or_create_adhoc_context=lambda: "adhoc"),
    )
    monkeypatch.setitem(sys.modules, "src.db", fake_db)
    assert get_db_context_or_default() == "adhoc"
