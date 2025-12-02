import asyncio
import pytest
from pathlib import Path

from scripts import run_product_owner as mod


def test_generate_requires_requirements(monkeypatch, tmp_path):
    # Point planning and artifacts to temp, ensure no requirements.yaml present
    monkeypatch.setattr(mod, "PLANNING", tmp_path / "planning")
    monkeypatch.setattr(mod, "ART", tmp_path / "artifacts")
    monkeypatch.setattr(mod, "VISION_PATH", tmp_path / "vision.yaml")
    monkeypatch.setattr(mod, "REVIEW_PATH", tmp_path / "review.yaml")
    monkeypatch.setattr(mod, "DEBUG_PATH", tmp_path / "debug.txt")
    monkeypatch.setattr(mod, "ensure_dirs", lambda: None)
    monkeypatch.setenv("CONCEPT", "")
    with pytest.raises(SystemExit):
        asyncio.run(mod.main())
