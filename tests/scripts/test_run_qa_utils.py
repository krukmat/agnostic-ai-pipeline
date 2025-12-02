import pathlib
from scripts import run_qa


def test_has_any_test_and_web(tmp_path):
    be_dir = tmp_path / "backend-fastapi" / "tests"
    be_dir.mkdir(parents=True)
    (be_dir / "test_api.py").write_text("pass", encoding="utf-8")
    web_root = tmp_path / "web-express"
    web_tests = web_root / "tests"
    web_tests.mkdir(parents=True)
    (web_tests / "something.test.js").write_text("//", encoding="utf-8")

    assert run_qa.has_any_test(be_dir) is True
    assert run_qa.has_any_web_test(web_root) is True


def test_has_any_test_empty(tmp_path):
    be_dir = tmp_path / "backend-fastapi" / "tests"
    be_dir.mkdir(parents=True)
    assert run_qa.has_any_test(be_dir) is False
