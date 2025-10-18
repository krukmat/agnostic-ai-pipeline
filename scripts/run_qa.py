# scripts/run_qa.py
from __future__ import annotations
import os, sys, json, subprocess, pathlib, shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "qa"
ART.mkdir(parents=True, exist_ok=True)
REPORT = ART / "last_report.json"

def has_any_test(py_dir: pathlib.Path) -> bool:
    if not py_dir.exists(): return False
    for p in py_dir.rglob("test_*.py"):
        return True
    for p in py_dir.rglob("*_test.py"):
        return True
    return False

def has_any_web_test(web_dir: pathlib.Path) -> bool:
    if not web_dir.exists(): return False
    tests = web_dir / "tests"
    if not tests.exists(): return False
    for p in tests.rglob("*.test.js"):
        return True
    for p in tests.rglob("*.test.ts"):
        return True
    return False

def run_cmd(cmd, cwd=None) -> int:
    try:
        print(f"[QA] run: {' '.join(cmd)} (cwd={cwd or os.getcwd()})")
        res = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (ART / "logs.txt").write_text(res.stdout, encoding="utf-8")
        print(res.stdout)
        return res.returncode
    except FileNotFoundError:
        return 127

def main():
    allow_no_tests = os.environ.get("ALLOW_NO_TESTS", "0") == "1"

    # Backend
    be_root = ROOT / "project" / "backend-fastapi"
    be_tests = be_root / "tests"
    be_has = has_any_test(be_tests)
    be_rc = None
    if be_has:
        pytest_bin = be_root / ".venv" / "bin" / "pytest"
        if pytest_bin.exists():
            be_rc = run_cmd([str(pytest_bin), "-q", "--disable-warnings", "--maxfail=1"], cwd=str(be_root))
        else:
            be_rc = 127  # venv/pytest no disponible
    else:
        be_rc = 10  # no tests

    # Web
    web_root = ROOT / "project" / "web-express"
    web_tests = has_any_web_test(web_root)
    web_rc = None
    if web_tests and (web_root / "package.json").exists():
        # Usamos npm por compatibilidad
        web_rc = run_cmd(["npm", "test", "--silent", "--", "--passWithNoTests"], cwd=str(web_root))
    else:
        web_rc = 10  # no tests

    # Agregables: mobile etc. (por ahora omitimos)
    areas = {
        "backend": {"has_tests": be_has, "rc": be_rc},
        "web":     {"has_tests": web_tests, "rc": web_rc},
    }

    any_fail = any(v["rc"] not in (0,10) for v in areas.values())
    any_no_tests = any(v["rc"] == 10 for v in areas.values())

    if any_fail:
        status = "fail"
        code = 2
    elif any_no_tests and not allow_no_tests:
        status = "no_tests"
        code = 3
    else:
        status = "pass"
        code = 0

    report = {
        "status": status,
        "allow_no_tests": allow_no_tests,
        "areas": areas,
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[QA] status={status} (detalle en {REPORT})")
    sys.exit(code)

if __name__ == "__main__":
    main()

