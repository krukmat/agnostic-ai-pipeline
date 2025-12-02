from pathlib import Path

from scripts import run_qa


def test_analyze_test_failures_env_errors(tmp_path):
    art = tmp_path
    (art / "pytest_output.txt").write_text("ERROR collecting test_bad.py\nModuleNotFoundError: No module named 'foo'\n", encoding="utf-8")
    (art / "npm_output.txt").write_text("TypeError: boom", encoding="utf-8")
    details = run_qa.analyze_test_failures(art, areas=("backend", "web"), be_rc=127, web_rc=127)
    assert details["backend"]["errors"]
    assert details["web"]["errors"]


def test_extract_pytest_errors_and_warnings():
    log = "ERROR collecting test_demo.py\nline 1\nFAILED test_demo.py::test_one\nAssertionError: fail\nwarning: something\n"
    errs = run_qa.extract_pytest_errors(log)
    warns = run_qa.extract_pytest_warnings(log)
    assert errs
    assert isinstance(warns, list)


def test_extract_npm_errors():
    log = "npm ERR! TypeError: boom\n    at Object.<anonymous>\n"
    out = run_qa.extract_npm_errors(log)
    assert isinstance(out, list)
