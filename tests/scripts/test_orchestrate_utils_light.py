import types

from scripts import orchestrate as orch


class DummyDbCtx:
    def __init__(self):
        self.enabled = True
        self.iteration_id = "it-1"
        self.updated = []

    def update_story_status(self, sid, status):
        self.updated.append((sid, status))


def test_load_stories_prefers_db(monkeypatch):
    dummy_ctx = DummyDbCtx()
    monkeypatch.setattr(orch, "get_current_context", lambda: dummy_ctx)
    monkeypatch.setattr(orch, "load_stories_from_db", lambda iteration_id: [{"id": "S1"}])
    stories = orch.load_stories()
    assert stories == [{"id": "S1"}]


def test_recover_yaml_automatic_uncomments_and_acceptance(monkeypatch):
    text = "# - id: S1\n#   acceptance: do X; do Y\n"
    recovered = orch.recover_yaml_automatic(text)
    assert isinstance(recovered, list)
    assert recovered[0]["id"] == "S1"
    assert recovered[0]["acceptance"] in (["do X", "do Y"], "do X; do Y")


def test_save_stories_syncs_db(monkeypatch, tmp_path):
    dummy_ctx = DummyDbCtx()
    monkeypatch.setattr(orch, "get_current_context", lambda: dummy_ctx)
    monkeypatch.setattr(orch, "STORIES_P", tmp_path / "stories.yaml")
    stories = [{"id": "S1", "status": "in_review"}]
    orch.save_stories(stories)
    assert (tmp_path / "stories.yaml").exists()
    assert dummy_ctx.updated == [("S1", "in_review")]
