from pathlib import Path

from scripts import run_qa


def test_load_dev_snapshot_reads_files(tmp_path, monkeypatch):
    monkeypatch.setattr(run_qa, "DEV_ART_DIR", tmp_path)
    story_dir = tmp_path / "S1"
    story_dir.mkdir()
    files = [{"path": "project/backend-fastapi/app/main.py"}]
    (story_dir / "files.json").write_text(run_qa.json.dumps(files), encoding="utf-8")
    assert run_qa.load_dev_snapshot("S1") == ["project/backend-fastapi/app/main.py"]


def test_log_contains_import_error(tmp_path):
    log_dir = tmp_path / "S1"
    log_dir.mkdir()
    log_path = log_dir / "logs.txt"
    log_path.write_text("ModuleNotFoundError: No module named 'foo'\n", encoding="utf-8")
    missing = run_qa.log_contains_import_error(log_dir)
    assert missing == ["foo"]


def test_fix_backend_test_imports(tmp_path):
    tests_dir = tmp_path / "project" / "backend-fastapi" / "tests"
    tests_dir.mkdir(parents=True)
    test_file = tests_dir / "test_demo.py"
    test_file.write_text("from project.backend-fastapi.app import main\n", encoding="utf-8")
    changed = run_qa.fix_backend_test_imports(tests_dir)
    assert changed is True
    assert "project.backend-fastapi" not in test_file.read_text(encoding="utf-8")


def test_analyze_test_failures_collects_errors(tmp_path):
    art_dir = tmp_path
    pytest_log = art_dir / "pytest_output.txt"
    pytest_log.write_text("FAILED test_demo.py::test_one\nModuleNotFoundError: No module named 'foo'\n", encoding="utf-8")
    npm_log = art_dir / "npm_output.txt"
    npm_log.write_text("TypeError: boom", encoding="utf-8")
    details = run_qa.analyze_test_failures(art_dir, areas=("backend",), be_rc=127, web_rc=0)
    assert details["backend"]["errors"]  # includes pytest parsing and env error
    # Web errors may be empty if npm parsing does not find patterns, but structure should exist
    assert "errors" in details["web"]
