from pathlib import Path

from scripts import common


def test_load_a2a_config_sanitizes(monkeypatch):
    monkeypatch.setattr(
        common,
        "load_config",
        lambda: {"a2a": {"agents": "not-a-dict", "authentication": "none", "extra": 1}},
    )
    out = common.load_a2a_config()
    assert out["agents"] == {}
    assert out["authentication"] == {"mode": "none"}
    assert out["extra"] == 1


def test_ensure_dirs_copies_defaults(tmp_path, monkeypatch):
    # Point module paths to temp
    monkeypatch.setattr(common, "ROOT", tmp_path)
    monkeypatch.setattr(common, "ART", tmp_path / "artifacts")
    monkeypatch.setattr(common, "PLANNING", tmp_path / "planning")
    monkeypatch.setattr(common, "PROJECT", tmp_path / "project")
    monkeypatch.setattr(common, "DEFAULTS", tmp_path / "project-defaults")

    # Seed defaults with a file
    default_file = common.DEFAULTS / "backend-fastapi" / "app.py"
    default_file.parent.mkdir(parents=True, exist_ok=True)
    default_file.write_text("print('hi')", encoding="utf-8")

    common.ensure_dirs()

    # Should create directories and copy defaults
    assert common.ART.exists()
    assert common.PLANNING.exists()
    copied = common.PROJECT / "backend-fastapi" / "app.py"
    assert copied.exists()
    assert copied.read_text(encoding="utf-8") == "print('hi')"
