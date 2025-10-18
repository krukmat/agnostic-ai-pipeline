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

def analyze_test_failures(areas):
    """Analiza los logs de test para extraer detalles específicos de fallos"""
    failure_details = {
        "backend": {"errors": [], "warnings": [], "missing_coverage": []},
        "web": {"errors": [], "warnings": [], "missing_coverage": []}
    }

    # Analizar logs de backend (pytest)
    pytest_log = ART / "pytest_output.txt"
    if pytest_log.exists():
        pytest_output = pytest_log.read_text(encoding="utf-8")
        failure_details["backend"]["errors"].extend(extract_pytest_errors(pytest_output))
        failure_details["backend"]["warnings"].extend(extract_pytest_warnings(pytest_output))

    # Analizar logs de web (npm test - jest)
    npm_log = ART / "npm_output.txt"
    if npm_log.exists():
        npm_output = npm_log.read_text(encoding="utf-8")
        failure_details["web"]["errors"].extend(extract_npm_errors(npm_output))

    return failure_details

def extract_pytest_errors(output: str):
    """Extrae errores específicos de pytest"""
    errors = []
    lines = output.split('\n')
    for i, line in enumerate(lines):
        # Buscar patrones de error de pytest
        if 'FAILED' in line and '::' in line:
            test_name = line.strip().split('::')[-1].split()[0]
            # Obtener líneas de error siguientes
            error_detail = []
            for j in range(i+1, min(i+10, len(lines))):
                if lines[j].strip() and not lines[j].startswith('='):
                    error_detail.append(lines[j])
                    if 'AssertionError' in lines[j] or 'Exception' in lines[j]:
                        break
            errors.append({
                "test": test_name,
                "error": '\n'.join(error_detail[:3]),  # Primeros 3 líneas de error
                "type": "pytest_failure"
            })
        elif 'ERROR' in line and '::' in line:
            test_name = line.strip().split('::')[-1].split()[0]
            errors.append({
                "test": test_name,
                "error": "Error de configuración o import",
                "type": "pytest_error"
            })
    return errors

def extract_pytest_warnings(output: str):
    """Extrae warnings de pytest"""
    warnings = []
    if 'no tests ran' in output.lower():
        warnings.append("No se encontraron tests para ejecutar")
    if 'warning' in output.lower():
        warnings.append("Hay warnings en la ejecución de tests")
    return warnings

def extract_npm_errors(output: str):
    """Extrae errores específicos de npm/jest"""
    errors = []
    lines = output.split('\n')
    for i, line in enumerate(lines):
        # Buscar failed tests en Jest
        if '✗' in line or '✕' in line:
            # Extraer nombre del test
            test_info = []
            for j in range(max(0, i-3), min(i+5, len(lines))):
                test_info.append(lines[j])
            clean_test_info = '\n'.join(test_info).strip()
            errors.append({
                "test": "Unknown test",
                "error": clean_test_info,
                "type": "jest_failure"
            })
    return errors

def run_cmd(cmd, cwd=None) -> int:
    try:
        print(f"[QA] run: {' '.join(cmd)} (cwd={cwd or os.getcwd()})")
        res = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        # Guardar logs separados por tipo de test
        log_file = ART / f"{cmd[0] if cmd else 'unknown'}_output.txt"
        log_file.write_text(res.stdout, encoding="utf-8")

        # También mantener el archivo general de logs
        (ART / "logs.txt").write_text(res.stdout, encoding="utf-8")
        print(res.stdout)
        return res.returncode
    except FileNotFoundError as e:
        error_msg = f"Command not found: {cmd[0] if cmd else 'unknown'} - {e}"
        (ART / "logs.txt").write_text(error_msg, encoding="utf-8")
        print(error_msg)
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

    # Análisis detallado de fallos
    failure_details = analyze_test_failures(areas)

    report = {
        "status": status,
        "allow_no_tests": allow_no_tests,
        "areas": areas,
        "failure_details": failure_details,
        "story_context": os.environ.get("STORY", ""),  # Contexto de la historia actual
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[QA] status={status} (detalle en {REPORT})")
    sys.exit(code)

if __name__ == "__main__":
    main()
