from scripts import run_cleanup as rc


def test_main_env_flush(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(rc, "cleanup_artifacts_and_planning", lambda flush_all: print(f"flush={flush_all}"))
    monkeypatch.setenv("FLUSH", "1")
    rc.main()
    out = capsys.readouterr().out
    assert "flush=True" in out
