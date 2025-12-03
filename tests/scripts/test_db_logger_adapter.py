from scripts.utils.db_logger import DbLogger


class DummyCtx:
    def __init__(self, enabled=True, fail=False):
        self.enabled = enabled
        self.fail = fail
        self.events = []
        self.artifacts = []
        self.attempts = []

    def log_event(self, *a, **k):
        if self.fail:
            raise RuntimeError("fail")
        self.events.append((a, k))

    def save_artifact(self, *a, **k):
        if self.fail:
            raise RuntimeError("fail")
        self.artifacts.append((a, k))

    def log_attempt(self, **k):
        if self.fail:
            raise RuntimeError("fail")
        self.attempts.append(k)


def test_db_logger_enabled_calls():
    ctx = DummyCtx(enabled=True)
    db = DbLogger(ctx)
    assert db.enabled
    assert db.log_event("start", role="r")
    assert db.save_artifact("r", "name", "val")
    assert db.log_attempt(story_id="S1", role="r", provider="p", model="m", status="ok")
    assert ctx.events and ctx.artifacts and ctx.attempts


def test_db_logger_disabled_noops():
    ctx = DummyCtx(enabled=False)
    db = DbLogger(ctx)
    assert db.enabled is False
    assert db.log_event("x") is False
    assert db.save_artifact("x", "y", "z") is False
    assert db.log_attempt(story_id="S1", role="r", provider="p", model="m", status="ok") is False
