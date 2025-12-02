import pytest

from scripts import run_product_owner as po


def test_grab_block_no_match():
    assert po.grab_block("no block here", "yaml", "VISION") == ""


def test_run_dspy_program_missing_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(po, "ROOT", tmp_path)
    # Snapshot path will be missing -> should raise SystemExit
    with pytest.raises(SystemExit):
        import asyncio
        asyncio.run(po.run_dspy_program("", "", ""))
