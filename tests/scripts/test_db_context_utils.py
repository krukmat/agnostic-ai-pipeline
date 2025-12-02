from scripts.utils import db_context as dbc


def test_get_db_context_or_default_disabled(monkeypatch):
    class DummyCtx:
        enabled = False
    monkeypatch.setattr(dbc, "AdHocContext", DummyCtx)
    ctx = dbc.get_db_context_or_default()
    assert hasattr(ctx, "enabled")


def test_get_db_context_or_default_default(monkeypatch):
    ctx = dbc.get_db_context_or_default()
    assert hasattr(ctx, "enabled")
