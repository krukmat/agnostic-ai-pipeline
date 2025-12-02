import pytest

from scripts import run_product_owner as po


@pytest.mark.asyncio
async def test_main_missing_requirements(monkeypatch, tmp_path):
    # Redirect paths
    monkeypatch.setattr(po, "PLANNING", tmp_path / "planning")
    monkeypatch.setattr(po, "ART", tmp_path / "artifacts")
    po.PLANNING.mkdir(parents=True, exist_ok=True)
    po.ART.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(po, "ensure_dirs", lambda: None)
    with pytest.raises(SystemExit):
        await po.main()
