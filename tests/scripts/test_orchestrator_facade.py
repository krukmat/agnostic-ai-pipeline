import datetime as dt
from pathlib import Path

from scripts.utils import orchestrator_facade as facade


def test_derive_max_loops_respects_explicit():
    out = facade.derive_max_loops(5, loops_arg_provided=True, loops_env_provided=False)
    assert out == 5


def test_derive_max_loops_from_todos(tmp_path, monkeypatch):
    stories_path = tmp_path / "stories.yaml"
    stories_path.write_text(
        "stories:\n- id: S1\n  status: todo\n- id: S2\n  status: todo\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(facade, "PLANNING", tmp_path)
    loops = facade.derive_max_loops(
        1,
        loops_arg_provided=False,
        loops_env_provided=False,
        planning_path=tmp_path,
    )
    assert loops == 2  # derived from todo count


def test_build_loop_env_sets_flags():
    env = facade.build_loop_env("Concept", allow_no_tests=True, max_loops=3)
    assert env["MAX_LOOPS"] == "3"
    assert env["ALLOW_NO_TESTS"] == "1"
    assert env["CONCEPT"] == "Concept"


def test_default_iteration_name_is_timestamp():
    name = facade.default_iteration_name(dt.datetime(2024, 1, 2, 3, 4, 5))
    assert name.startswith("iteration-20240102-030405")
