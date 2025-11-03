# Fase 0: Auditoría Técnica Python 3.10+ Migration

**Objetivo**: Identificar todos los breaking changes, incompatibilidades y riesgos antes de migrar de Python 3.9.10 → 3.11.9

**Duración estimada**: 4-6 horas
**Output**: Informe técnico con decisión Go/No-Go

---

## 1. Análisis de Dependencias (90 min)

### 1.1 Inventario Completo de Dependencias

```bash
# Crear directorio de trabajo para auditoría
mkdir -p /tmp/py311_audit
cd /Users/matiasleandrokruk/Documents/agnostic-ai-pipeline

# Exportar todas las dependencias actuales (con versiones exactas)
.venv/bin/pip freeze > /tmp/py311_audit/current_deps_py39.txt

# Listar solo deps directas (sin transitivas)
cat requirements.txt | grep -v "^#" | grep -v "^$" > /tmp/py311_audit/direct_deps.txt

echo "📦 Dependencias directas:"
cat /tmp/py311_audit/direct_deps.txt
```

**Expected output**:
```
httpx>=0.25
PyYAML>=6.0
typer>=0.12
rich>=13.7
pytest>=8.0
fastapi
fastapi>=0.112
uvicorn
google-genai>=0.6.0
rorf>=0.1.0
uvicorn
```

### 1.2 Verificación de Compatibilidad PyPI

Para cada dependencia, verificar en PyPI si soporta Python 3.11:

```python
#!/usr/bin/env python3
# scripts/check_py311_compat.py
"""
Verifica compatibilidad Python 3.11 de todas las dependencias.
Consulta PyPI API para cada paquete.
"""
import httpx
import re
from pathlib import Path

def parse_requirement(line):
    """Parse 'package>=version' → (package, version_spec)"""
    match = re.match(r'^([a-zA-Z0-9_-]+)([>=<]+.*)?$', line.strip())
    if match:
        return match.group(1), match.group(2) or ""
    return None, None

def check_pypi_compatibility(package_name):
    """
    Consulta PyPI JSON API para verificar Python 3.11 support.
    Returns: dict con info de compatibilidad
    """
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Obtener classifiers
        classifiers = data.get('info', {}).get('classifiers', [])

        # Buscar Python version classifiers
        py_versions = [c for c in classifiers if c.startswith('Programming Language :: Python :: 3')]

        # Check específico para 3.11
        supports_311 = any('3.11' in c for c in py_versions)
        supports_310 = any('3.10' in c for c in py_versions)

        # Última versión
        latest_version = data.get('info', {}).get('version', 'unknown')

        return {
            'package': package_name,
            'latest_version': latest_version,
            'supports_3.10': supports_310,
            'supports_3.11': supports_311,
            'python_versions': py_versions,
            'status': 'OK' if supports_311 else ('PARTIAL' if supports_310 else 'UNKNOWN')
        }
    except httpx.HTTPError as e:
        return {
            'package': package_name,
            'status': 'ERROR',
            'error': str(e)
        }

def main():
    deps_file = Path('requirements.txt')
    if not deps_file.exists():
        print("❌ requirements.txt not found")
        return

    results = []

    with open(deps_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            package, version_spec = parse_requirement(line)
            if not package:
                continue

            print(f"🔍 Checking {package}...", end=" ")
            result = check_pypi_compatibility(package)
            results.append(result)

            status_emoji = {
                'OK': '✅',
                'PARTIAL': '⚠️',
                'UNKNOWN': '❓',
                'ERROR': '❌'
            }.get(result['status'], '❓')

            print(f"{status_emoji} {result['status']}")

    # Reporte final
    print("\n" + "="*70)
    print("COMPATIBILITY REPORT")
    print("="*70)

    ok_count = sum(1 for r in results if r['status'] == 'OK')
    partial_count = sum(1 for r in results if r['status'] == 'PARTIAL')
    unknown_count = sum(1 for r in results if r['status'] == 'UNKNOWN')
    error_count = sum(1 for r in results if r['status'] == 'ERROR')

    print(f"✅ Compatible with Python 3.11: {ok_count}/{len(results)}")
    print(f"⚠️  Partially compatible (3.10 only): {partial_count}/{len(results)}")
    print(f"❓ Unknown (no classifiers): {unknown_count}/{len(results)}")
    print(f"❌ Errors: {error_count}/{len(results)}")

    # Detalles de problemas
    if partial_count + unknown_count + error_count > 0:
        print("\n⚠️  PACKAGES REQUIRING ATTENTION:")
        for r in results:
            if r['status'] != 'OK':
                print(f"  - {r['package']}: {r['status']}")
                if 'error' in r:
                    print(f"    Error: {r['error']}")
                elif 'python_versions' in r and r['python_versions']:
                    print(f"    Supported: {', '.join(r['python_versions'][-3:])}")

    # Exportar JSON
    import json
    output_file = Path('/tmp/py311_audit/pypi_compat_report.json')
    output_file.write_text(json.dumps(results, indent=2))
    print(f"\n📄 Full report: {output_file}")

if __name__ == '__main__':
    main()
```

**Ejecutar**:
```bash
python scripts/check_py311_compat.py
```

**Expected findings**:
- `httpx>=0.25`: ✅ Soporta 3.11
- `PyYAML>=6.0`: ✅ Soporta 3.11
- `typer>=0.12`: ✅ Soporta 3.11
- `fastapi>=0.112`: ✅ Soporta 3.11
- `google-genai>=0.6.0`: ⚠️ Verificar (Google SDK puede tener retrasos)
- `rorf>=0.1.0`: ❓ Paquete custom, verificar manualmente

### 1.3 Verificación Manual de Paquetes Custom

```bash
# rorf parece ser paquete custom (no está en PyPI público)
# Verificar dónde se instala
.venv/bin/pip show rorf

# Si falla, buscar en código dónde se usa
grep -r "import rorf" scripts/ a2a/ src/
grep -r "from rorf" scripts/ a2a/ src/

# Si es crítico, verificar si tiene setup.py con python_requires
find .venv/lib/python3.9/site-packages/rorf* -name "setup.py" -o -name "pyproject.toml"
```

**Acción**: Documentar en informe si `rorf` necesita actualización o si es opcional.

---

## 2. Análisis de Código Python (120 min)

### 2.1 Detección de Imports Deprecated

Python 3.10+ movió varios tipos de `typing` a `collections.abc`:

```bash
# Buscar imports problemáticos
echo "🔍 Checking for deprecated typing imports..."

# typing.List, Dict, Set, Tuple → list, dict, set, tuple (built-ins desde 3.9)
grep -rn "from typing import.*List" scripts/ a2a/ src/ || echo "✅ No List imports"
grep -rn "from typing import.*Dict" scripts/ a2a/ src/ || echo "✅ No Dict imports"
grep -rn "from typing import.*Set" scripts/ a2a/ src/ || echo "✅ No Set imports"
grep -rn "from typing import.*Tuple" scripts/ a2a/ src/ || echo "✅ No Tuple imports"

# collections.Callable, Iterable, etc. → collections.abc (deprecados en 3.9, removidos en 3.10)
grep -rn "from collections import.*Callable" scripts/ a2a/ src/ || echo "✅ No collections.Callable"
grep -rn "from collections import.*Iterable" scripts/ a2a/ src/ || echo "✅ No collections.Iterable"
grep -rn "from collections import.*Mapping" scripts/ a2a/ src/ || echo "✅ No collections.Mapping"

# Guardar resultados
{
  echo "=== DEPRECATED IMPORTS AUDIT ==="
  grep -rn "from typing import.*List" scripts/ a2a/ src/ 2>/dev/null || echo "NONE: typing.List"
  grep -rn "from collections import.*Callable" scripts/ a2a/ src/ 2>/dev/null || echo "NONE: collections.Callable"
} > /tmp/py311_audit/deprecated_imports.txt

cat /tmp/py311_audit/deprecated_imports.txt
```

**Automatic Fix Script**:
```python
#!/usr/bin/env python3
# scripts/fix_deprecated_imports.py
"""
Reemplaza imports deprecated automáticamente.
CUIDADO: Revisar diffs antes de commitear.
"""
import re
from pathlib import Path

REPLACEMENTS = {
    # typing.List → list, etc. (Python 3.9+)
    r'from typing import (.*\b)List(\b.*)': r'from typing import \1list\2',
    r'from typing import (.*\b)Dict(\b.*)': r'from typing import \1dict\2',
    r'from typing import (.*\b)Set(\b.*)': r'from typing import \1set\2',
    r'from typing import (.*\b)Tuple(\b.*)': r'from typing import \1tuple\2',

    # collections → collections.abc (Python 3.10+)
    r'from collections import (.*\b)(Callable|Iterable|Iterator|Mapping|MutableMapping)':
        r'from collections.abc import \1\2',
}

def fix_file(file_path):
    """Aplica fixes a un archivo."""
    content = file_path.read_text()
    original = content

    for pattern, replacement in REPLACEMENTS.items():
        content = re.sub(pattern, replacement, content)

    if content != original:
        print(f"  🔧 Fixed: {file_path}")
        file_path.write_text(content)
        return True
    return False

def main():
    fixed_count = 0

    for directory in ['scripts', 'a2a', 'src']:
        if not Path(directory).exists():
            continue

        for py_file in Path(directory).rglob('*.py'):
            if fix_file(py_file):
                fixed_count += 1

    print(f"\n✅ Fixed {fixed_count} files")
    print("⚠️  Review changes with: git diff")

if __name__ == '__main__':
    main()
```

### 2.2 Verificación de Type Hints Modernos

Python 3.10 introduce `|` operator para Union types:

```bash
# Verificar si ya se usa (no debería en código 3.9)
grep -rn " | " scripts/ a2a/ src/ | grep -v "^Binary" | grep -v ".pyc" > /tmp/py311_audit/pipe_operator.txt

# Contar ocurrencias de Union vs | syntax
union_count=$(grep -r "Union\[" scripts/ a2a/ src/ 2>/dev/null | wc -l)
pipe_count=$(grep -r ": .*|.*=" scripts/ a2a/ src/ 2>/dev/null | wc -l)

echo "Union[...] syntax: $union_count occurrences"
echo "| syntax: $pipe_count occurrences"

# Union[...] funciona en 3.10+, pero | es más moderno
# Acción: Opcional modernizar después de migración
```

### 2.3 Detección de Features Python 3.10+

```bash
# match/case (structural pattern matching, nuevo en 3.10)
# Si ya se usa, código NO funciona en 3.9
grep -rn "match " scripts/ a2a/ src/ | grep -v "re.match" | grep -v "# match" > /tmp/py311_audit/match_case.txt

if [[ -s /tmp/py311_audit/match_case.txt ]]; then
  echo "⚠️  WARNING: match/case encontrado (requiere 3.10+)"
  cat /tmp/py311_audit/match_case.txt
else
  echo "✅ No match/case syntax (compatible con 3.9)"
fi

# Parenthesized context managers (nuevo en 3.10)
# with (open(...) as f, open(...) as g):
grep -rn "with (" scripts/ a2a/ src/ > /tmp/py311_audit/paren_context.txt

# TypeAlias (PEP 613, 3.10+)
grep -rn "TypeAlias" scripts/ a2a/ src/ > /tmp/py311_audit/type_alias.txt
```

### 2.4 Análisis Estático con Vermin

Vermin detecta versión mínima de Python requerida:

```bash
# Instalar vermin
pip install vermin

# Analizar todo el código
vermin -t=3.9- scripts/ a2a/ src/ > /tmp/py311_audit/vermin_report.txt

# Revisar report
cat /tmp/py311_audit/vermin_report.txt

# Expected output:
# Minimum required versions: 3.9
# Incompatible versions:     (none)
```

**Interpretación**:
- Si dice "Minimum: 3.9" → Compatible con 3.10+
- Si dice "Minimum: 3.10" → Ya usa features 3.10 (no debería)
- Si lista "Incompatible: 3.10" → Hay código que NO funciona en 3.10

---

## 3. Testing Baseline en Python 3.9 (60 min)

### 3.1 Ejecutar Suite Completa de Tests

```bash
# Activar entorno Python 3.9
source .venv/bin/activate
python --version  # Verificar 3.9.10

# Ejecutar tests con coverage
.venv/bin/pytest tests/ -v --tb=short --maxfail=5 > /tmp/py311_audit/py39_test_results.txt 2>&1

# Guardar exit code
echo $? > /tmp/py311_audit/py39_test_exitcode.txt

# Summary
tail -20 /tmp/py311_audit/py39_test_results.txt
```

**Capturar métricas**:
```bash
# Contar tests passed/failed
grep -E "passed|failed|error" /tmp/py311_audit/py39_test_results.txt | tail -1 > /tmp/py311_audit/py39_test_summary.txt

# Ejemplo output esperado:
# ===== 45 passed, 2 failed, 1 error in 23.45s =====

cat /tmp/py311_audit/py39_test_summary.txt
```

### 3.2 Identificar Tests que Dependen de Python Version

```bash
# Buscar tests que usen sys.version_info
grep -rn "sys.version_info" tests/ > /tmp/py311_audit/version_dependent_tests.txt

# Buscar skipif basados en version
grep -rn "skipif.*python" tests/ >> /tmp/py311_audit/version_dependent_tests.txt

# Buscar pytest markers de versión
grep -rn "@pytest.mark.python" tests/ >> /tmp/py311_audit/version_dependent_tests.txt

cat /tmp/py311_audit/version_dependent_tests.txt
```

### 3.3 Smoke Tests Críticos

Ejecutar manualmente comandos core para establecer baseline:

```bash
# Test 1: BA role
echo "Test 1: BA role" > /tmp/py311_audit/smoke_tests.log
timeout 60 make ba CONCEPT="Test app" >> /tmp/py311_audit/smoke_tests.log 2>&1 && echo "✅ PASS" || echo "❌ FAIL"

# Test 2: Architect role
echo "Test 2: Architect" >> /tmp/py311_audit/smoke_tests.log
timeout 60 make plan >> /tmp/py311_audit/smoke_tests.log 2>&1 && echo "✅ PASS" || echo "❌ FAIL"

# Test 3: LLM client
echo "Test 3: LLM client" >> /tmp/py311_audit/smoke_tests.log
python -c "from scripts.llm import Client; c = Client(role='ba'); print('OK')" >> /tmp/py311_audit/smoke_tests.log 2>&1 && echo "✅ PASS" || echo "❌ FAIL"
```

---

## 4. Configuración y CI/CD Analysis (45 min)

### 4.1 Verificar Archivos de Runtime

```bash
# Buscar todos los archivos que especifican Python version
find . -name ".python-version" -o -name "runtime.txt" -o -name "Dockerfile" -o -name ".github" -o -name "pyproject.toml" | grep -v ".venv" > /tmp/py311_audit/runtime_files.txt

cat /tmp/py311_audit/runtime_files.txt

# Inspeccionar cada uno
while read file; do
  echo "=== $file ==="
  cat "$file" | grep -i python
done < /tmp/py311_audit/runtime_files.txt > /tmp/py311_audit/runtime_configs.txt

cat /tmp/py311_audit/runtime_configs.txt
```

**Ejemplo findings**:
```
=== .python-version ===
3.9.10

=== Dockerfile ===
FROM python:3.9-slim
```

**Acción**: Documentar todos los archivos que necesitarán actualización.

### 4.2 Verificar Makefile

```bash
# Buscar referencias a Python version en Makefile
grep -n python Makefile > /tmp/py311_audit/makefile_python.txt

# Buscar definición de PY variable
grep -n "PY\s*=" Makefile >> /tmp/py311_audit/makefile_python.txt

cat /tmp/py311_audit/makefile_python.txt
```

**Ejemplo output**:
```
12:PY = .venv/bin/python
45:setup:
46:    python -m venv .venv
```

**Análisis**:
- Línea 46 usa `python` (resolverá a la versión de pyenv local si está configurado)
- ✅ No hardcodea 3.9, compatible

### 4.3 CI/CD Workflows

```bash
# GitHub Actions
if [[ -d .github/workflows ]]; then
  echo "=== GitHub Actions ===" > /tmp/py311_audit/cicd_config.txt
  grep -rn "python-version" .github/workflows/ >> /tmp/py311_audit/cicd_config.txt
fi

# GitLab CI
if [[ -f .gitlab-ci.yml ]]; then
  echo "=== GitLab CI ===" >> /tmp/py311_audit/cicd_config.txt
  grep -n "image.*python" .gitlab-ci.yml >> /tmp/py311_audit/cicd_config.txt
fi

# Otros
find . -name "*.yml" -o -name "*.yaml" | xargs grep -l "python.*3\." 2>/dev/null >> /tmp/py311_audit/cicd_config.txt

cat /tmp/py311_audit/cicd_config.txt
```

---

## 5. Breaking Changes Analysis (90 min)

### 5.1 Python 3.10 Breaking Changes

Verificar específicamente:

#### a) `collections` deprecations (PEP 585)

```python
# scripts/check_collections_abc.py
"""Detecta uso de collections deprecated."""
import ast
import sys
from pathlib import Path

DEPRECATED_COLLECTIONS = {
    'Callable', 'Iterable', 'Iterator', 'Mapping', 'MutableMapping',
    'Sequence', 'MutableSequence', 'Set', 'MutableSet'
}

class CollectionsVisitor(ast.NodeVisitor):
    def __init__(self):
        self.issues = []

    def visit_ImportFrom(self, node):
        if node.module == 'collections':
            for alias in node.names:
                if alias.name in DEPRECATED_COLLECTIONS:
                    self.issues.append({
                        'file': getattr(node, '_file', 'unknown'),
                        'line': node.lineno,
                        'import': alias.name,
                        'fix': f'from collections.abc import {alias.name}'
                    })
        self.generic_visit(node)

def check_file(file_path):
    try:
        tree = ast.parse(file_path.read_text())
        # Inject file path for reporting
        for node in ast.walk(tree):
            node._file = str(file_path)

        visitor = CollectionsVisitor()
        visitor.visit(tree)
        return visitor.issues
    except SyntaxError:
        return []

def main():
    all_issues = []

    for directory in ['scripts', 'a2a', 'src', 'tests']:
        if not Path(directory).exists():
            continue

        for py_file in Path(directory).rglob('*.py'):
            issues = check_file(py_file)
            all_issues.extend(issues)

    if all_issues:
        print("⚠️  DEPRECATED collections IMPORTS FOUND:")
        for issue in all_issues:
            print(f"  {issue['file']}:{issue['line']}")
            print(f"    Current: from collections import {issue['import']}")
            print(f"    Fix:     {issue['fix']}")
        print(f"\nTotal: {len(all_issues)} issues")
        return 1
    else:
        print("✅ No deprecated collections imports")
        return 0

if __name__ == '__main__':
    sys.exit(main())
```

```bash
python scripts/check_collections_abc.py > /tmp/py311_audit/collections_abc_issues.txt
```

#### b) `distutils` removal

```bash
# distutils está deprecated en 3.10, removed en 3.12
grep -rn "import distutils" scripts/ a2a/ src/ tests/ > /tmp/py311_audit/distutils_usage.txt

if [[ -s /tmp/py311_audit/distutils_usage.txt ]]; then
  echo "⚠️  distutils usage found (deprecated):"
  cat /tmp/py311_audit/distutils_usage.txt
  echo "ACTION: Replace with setuptools or packaging"
else
  echo "✅ No distutils usage"
fi
```

#### c) `asyncio` changes

```bash
# asyncio.coroutine decorator removido en 3.11
grep -rn "@asyncio.coroutine" scripts/ a2a/ src/ > /tmp/py311_audit/asyncio_decorator.txt

# loop parameter removido de muchas funciones asyncio en 3.10
grep -rn "loop=" scripts/ a2a/ src/ | grep asyncio > /tmp/py311_audit/asyncio_loop_param.txt

cat /tmp/py311_audit/asyncio_*.txt
```

### 5.2 Python 3.11 Breaking Changes

#### a) `tomllib` built-in

```bash
# toml parsing: verificar si usamos tomli/toml (reemplazable por tomllib en 3.11)
grep -rn "import toml" scripts/ a2a/ src/ > /tmp/py311_audit/toml_imports.txt

cat /tmp/py311_audit/toml_imports.txt
```

#### b) Exception groups (PEP 654)

```bash
# except* syntax nuevo en 3.11, no debería estar ya
grep -rn "except\*" scripts/ a2a/ src/ > /tmp/py311_audit/except_star.txt
```

---

## 6. Generación de Informe Final (30 min)

### 6.1 Compilar Findings

```python
#!/usr/bin/env python3
# scripts/generate_phase0_report.py
"""
Genera informe consolidado de Fase 0 audit.
"""
import json
from pathlib import Path
from datetime import datetime

AUDIT_DIR = Path('/tmp/py311_audit')

def load_json_report(filename):
    file_path = AUDIT_DIR / filename
    if file_path.exists():
        return json.loads(file_path.read_text())
    return None

def count_lines(filename):
    file_path = AUDIT_DIR / filename
    if file_path.exists():
        return len(file_path.read_text().strip().split('\n'))
    return 0

def main():
    report = []

    report.append("# Python 3.11 Migration Audit Report")
    report.append(f"**Generated**: {datetime.now().isoformat()}")
    report.append(f"**Current Python**: 3.9.10")
    report.append(f"**Target Python**: 3.11.9")
    report.append("")

    # 1. Dependencies
    report.append("## 1. Dependencies Analysis")
    pypi_report = load_json_report('pypi_compat_report.json')
    if pypi_report:
        ok_count = sum(1 for r in pypi_report if r.get('status') == 'OK')
        total = len(pypi_report)
        report.append(f"- ✅ Compatible: {ok_count}/{total}")
        report.append(f"- ⚠️  Issues: {total - ok_count}/{total}")

        issues = [r for r in pypi_report if r.get('status') != 'OK']
        if issues:
            report.append("\n**Packages with issues**:")
            for pkg in issues:
                report.append(f"  - `{pkg['package']}`: {pkg['status']}")

    # 2. Code analysis
    report.append("\n## 2. Code Analysis")
    deprecated_count = count_lines('deprecated_imports.txt')
    if deprecated_count > 0:
        report.append(f"- ⚠️  Deprecated imports: {deprecated_count} occurrences")
    else:
        report.append("- ✅ No deprecated imports")

    collections_count = count_lines('collections_abc_issues.txt')
    if collections_count > 0:
        report.append(f"- ⚠️  collections.abc issues: {collections_count}")
    else:
        report.append("- ✅ No collections.abc issues")

    # 3. Tests baseline
    report.append("\n## 3. Tests Baseline (Python 3.9)")
    test_summary_path = AUDIT_DIR / 'py39_test_summary.txt'
    if test_summary_path.exists():
        summary = test_summary_path.read_text().strip()
        report.append(f"```\n{summary}\n```")

    # 4. Configuration
    report.append("\n## 4. Configuration Files")
    runtime_files_count = count_lines('runtime_files.txt')
    report.append(f"- Files to update: {runtime_files_count}")

    # 5. Breaking changes
    report.append("\n## 5. Breaking Changes Detection")
    distutils_count = count_lines('distutils_usage.txt')
    asyncio_count = count_lines('asyncio_decorator.txt')

    if distutils_count > 0:
        report.append(f"- ⚠️  distutils usage: {distutils_count} occurrences (deprecated)")
    if asyncio_count > 0:
        report.append(f"- ⚠️  asyncio deprecated patterns: {asyncio_count}")

    if distutils_count == 0 and asyncio_count == 0:
        report.append("- ✅ No critical breaking changes detected")

    # 6. Decision
    report.append("\n## 6. Go/No-Go Decision")

    # Calculate blockers
    blockers = []
    if pypi_report:
        critical_deps = [r for r in pypi_report if r.get('status') == 'ERROR']
        if critical_deps:
            blockers.append(f"{len(critical_deps)} dependencies with errors")

    if distutils_count > 5:
        blockers.append(f"Heavy distutils usage ({distutils_count} occurrences)")

    if blockers:
        report.append("**Status**: ⛔ **NO-GO** (blockers found)")
        report.append("\n**Blockers**:")
        for blocker in blockers:
            report.append(f"  - {blocker}")
        report.append("\n**Action**: Resolve blockers before proceeding to Phase 1")
    else:
        report.append("**Status**: ✅ **GO** (proceed to Phase 1)")
        report.append("\n**Recommended actions**:")

        if deprecated_count > 0:
            report.append(f"  1. Fix {deprecated_count} deprecated imports (run `scripts/fix_deprecated_imports.py`)")
        if runtime_files_count > 0:
            report.append(f"  2. Update {runtime_files_count} configuration files")
        report.append("  3. Proceed with Phase 1 (Python 3.11 installation)")

    # Write report
    output_file = Path('docs/python310_migration_audit.md')
    output_file.parent.mkdir(exist_ok=True, parents=True)
    output_file.write_text('\n'.join(report))

    print(f"📄 Report generated: {output_file}")
    print("\n" + "="*70)
    print('\n'.join(report[-15:]))  # Print last 15 lines (decision section)

if __name__ == '__main__':
    main()
```

```bash
python scripts/generate_phase0_report.py
```

### 6.2 Review Checklist

Antes de aprobar Go decision:

```bash
# Checklist final
cat > /tmp/py311_audit/phase0_checklist.md <<'EOF'
# Phase 0 Completion Checklist

- [ ] Todas las dependencias verificadas en PyPI
- [ ] Script de compatibilidad ejecutado sin errors
- [ ] Código analizado con vermin
- [ ] Tests baseline ejecutados y documentados (exit code guardado)
- [ ] Deprecated imports identificados (y fix script disponible si hay)
- [ ] Archivos de configuración inventariados
- [ ] Breaking changes específicos verificados (collections, distutils, asyncio)
- [ ] Informe final generado en docs/python310_migration_audit.md
- [ ] Decision Go/No-Go documentada con justificación
- [ ] Si Go: Plan de fixes creado (qué arreglar antes de Phase 1)
- [ ] Si No-Go: Blockers identificados con acciones correctivas

## Decisión Final

**Status**: [ ] GO / [ ] NO-GO

**Signed by**: _________________
**Date**: _________________

## Next Steps

Si GO:
1. Ejecutar fixes automáticos (deprecated imports)
2. Actualizar archivos de configuración (.python-version, Dockerfile, etc.)
3. Commit changes: "chore: prepare for Python 3.11 migration"
4. Proceder a Phase 1

Si NO-GO:
1. Priorizar resolución de blockers
2. Re-ejecutar Phase 0 después de fixes
EOF

cat /tmp/py311_audit/phase0_checklist.md
```

---

## 7. Automatización Completa (Script All-in-One)

Para ejecutar toda la Fase 0 de una vez:

```bash
#!/bin/bash
# scripts/run_phase0_audit.sh
# Ejecuta auditoría completa Python 3.11 migration

set -e

AUDIT_DIR="/tmp/py311_audit"
PROJECT_ROOT="/Users/matiasleandrokruk/Documents/agnostic-ai-pipeline"

echo "🔍 Starting Phase 0 Audit..."
echo "Target: Python 3.9.10 → 3.11.9"
echo ""

# Setup
mkdir -p "$AUDIT_DIR"
cd "$PROJECT_ROOT"

# 1. Dependencies
echo "📦 [1/7] Analyzing dependencies..."
python scripts/check_py311_compat.py

# 2. Code analysis
echo "🔍 [2/7] Analyzing code for deprecated patterns..."
python scripts/check_collections_abc.py > "$AUDIT_DIR/collections_abc_issues.txt" || true

grep -rn "import distutils" scripts/ a2a/ src/ tests/ > "$AUDIT_DIR/distutils_usage.txt" || echo "None" > "$AUDIT_DIR/distutils_usage.txt"

# 3. Tests baseline
echo "🧪 [3/7] Running test baseline..."
source .venv/bin/activate
.venv/bin/pytest tests/ -v --tb=short > "$AUDIT_DIR/py39_test_results.txt" 2>&1 || true
echo $? > "$AUDIT_DIR/py39_test_exitcode.txt"

# 4. Configuration files
echo "⚙️  [4/7] Scanning configuration files..."
find . -name ".python-version" -o -name "Dockerfile" -o -name "*.yml" | grep -v ".venv" > "$AUDIT_DIR/runtime_files.txt"

# 5. Vermin analysis
echo "🐍 [5/7] Running vermin static analysis..."
pip install -q vermin
vermin -t=3.9- scripts/ a2a/ src/ > "$AUDIT_DIR/vermin_report.txt" || true

# 6. Generate report
echo "📄 [6/7] Generating audit report..."
python scripts/generate_phase0_report.py

# 7. Open report
echo "✅ [7/7] Audit complete!"
echo ""
echo "Report: docs/python310_migration_audit.md"
echo "Full audit data: $AUDIT_DIR"
echo ""

# Display decision
tail -20 docs/python310_migration_audit.md
```

**Ejecutar todo**:
```bash
bash scripts/run_phase0_audit.sh
```

---

## Tiempo Estimado por Sección

| Sección | Tiempo | Automático | Manual |
|---------|--------|------------|--------|
| 1. Dependencias | 90 min | ✅ 80% | 20% (custom packages) |
| 2. Código | 120 min | ✅ 90% | 10% (review fixes) |
| 3. Tests | 60 min | ✅ 100% | - |
| 4. Config | 45 min | ✅ 70% | 30% (CI/CD review) |
| 5. Breaking changes | 90 min | ✅ 80% | 20% (complex patterns) |
| 6. Informe | 30 min | ✅ 95% | 5% (decision) |
| 7. All-in-one | 5 min | ✅ 100% | - |

**Total**: ~6.5 horas
**Con automatización**: ~2 horas (solo review de outputs + decision)

---

## Outputs Finales Esperados

Al terminar Fase 0, deberías tener:

1. ✅ **`docs/python310_migration_audit.md`**: Informe técnico completo
2. ✅ **`/tmp/py311_audit/`**: 15+ archivos con datos raw
3. ✅ **Decision documentada**: GO o NO-GO con justificación
4. ✅ **Action plan**: Lista de fixes requeridos antes de Phase 1
5. ✅ **Baseline metrics**: Tests passing rate en Python 3.9

**Ejemplo de decisión GO**:
```markdown
## 6. Go/No-Go Decision

**Status**: ✅ **GO**

**Findings summary**:
- 9/10 dependencies compatible with Python 3.11
- 1 custom package (rorf) needs verification
- 3 deprecated imports detected (auto-fixable)
- 45/47 tests passing (baseline)
- No critical breaking changes

**Action plan before Phase 1**:
1. Run `python scripts/fix_deprecated_imports.py`
2. Update `.python-version` to 3.11.9
3. Update `Dockerfile` FROM python:3.11-slim
4. Verify rorf package locally
5. Commit changes

**Estimated effort**: 1 hour
**Risk level**: LOW
```

---

## Siguiente Paso

Si Fase 0 resulta en **GO**, proceder a `DSPY_COMPARISON_PLAN.md` Fase 1.
Si resulta en **NO-GO**, documentar blockers y crear issues para resolverlos.
