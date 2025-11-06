#!/usr/bin/env python3
"""
Verifica compatibilidad Python 3.11 de todas las dependencias.
Consulta PyPI API para cada paquete.

Usage:
    python scripts/check_py311_compat.py
"""
import httpx
import re
from pathlib import Path
import json


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
        return 1

    results = []

    with open(deps_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            package, version_spec = parse_requirement(line)
            if not package:
                continue

            print(f"🔍 Checking {package}...", end=" ", flush=True)
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
    output_file = Path('/tmp/py311_audit/pypi_compat_report.json')
    output_file.parent.mkdir(exist_ok=True, parents=True)
    output_file.write_text(json.dumps(results, indent=2))
    print(f"\n📄 Full report: {output_file}")

    return 1 if (error_count > 0 or partial_count > 2) else 0


if __name__ == '__main__':
    exit(main())
