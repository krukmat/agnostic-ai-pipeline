import asyncio

import pytest

from scripts import orchestrate as orch


@pytest.mark.asyncio
async def test_local_ba_requires_concept():
    res = await orch._local_business_analyst_handler()
    assert res["status"] == "error"


@pytest.mark.asyncio
async def test_local_ba_success(monkeypatch):
    async def fake_generate(concept):
        return {"concept": concept, "ok": True}
    monkeypatch.setattr(orch, "generate_requirements", fake_generate)
    res = await orch._local_business_analyst_handler(concept="demo")
    assert res["status"] == "ok"
    assert res["concept"] == "demo"


@pytest.mark.asyncio
async def test_local_po_handler(monkeypatch):
    async def fake_po():
        return None
    monkeypatch.setattr(orch, "run_po", fake_po)
    res = await orch._local_product_owner_handler()
    assert res["status"] == "ok"


@pytest.mark.asyncio
async def test_local_dev_handler_error(monkeypatch):
    async def fake_impl(story_id=None, retries=3):
        return {"status": "error", "story_id": story_id, "model_info": {"provider": "p", "model": "m"}}
    monkeypatch.setattr(orch, "implement_story", fake_impl)
    res = await orch._local_developer_handler(story_id="S1", retries="x")
    assert res["status"] == "error"
    assert res["story_id"] == "S1"


@pytest.mark.asyncio
async def test_local_qa_handler(monkeypatch):
    def fake_run_quality_checks(allow_no_tests=True, story=""):
        return {"status": "pass", "story": story}
    monkeypatch.setattr(orch, "run_quality_checks", fake_run_quality_checks)
    res = await orch._local_qa_handler(story_id="S2", allow_no_tests="1")
    assert res["status"] == "pass"
    assert res["story"] == "S2"
