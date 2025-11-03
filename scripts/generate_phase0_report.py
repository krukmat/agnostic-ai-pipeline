#!/usr/bin/env python3
"""
Genera informe consolidado de Fase 0 audit.

Usage:
    python scripts/generate_phase0_report.py
"""
import json
from pathlib import Path
from datetime import datetime

AUDIT_DIR = Path('/tmp/py311_audit')


def load_json_report(filename):
    file_path = AUDIT_DIR / filename
    if file_path.exists():
        try:
            return json.loads(file_path.read_text())
        except json.JSONDecodeError:
            return None
    return None


def count_lines(filename):
    file_path = AUDIT_DIR / filename
    if file_path.exists():
        content = file_path.read_text().strip()
        if not content or content == "None":
            return 0
        return len(content.split('\n'))
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
                if 'error' in pkg:
                    report.append(f"    Error: {pkg['error']}")
    else:
        report.append("- ⚠️  PyPI report not found (run check_py311_compat.py)")

    # 2. Code analysis
    report.append("\n## 2. Code Analysis")
    deprecated_count = count_lines('deprecated_imports.txt')
    if deprecated_count > 0:
        report.append(f"- ⚠️  Deprecated imports: {deprecated_count} occurrences")
    else:
        report.append("- ✅ No deprecated imports detected")

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
    else:
        report.append("- ⚠️  Test baseline not run")

    # 4. Configuration
    report.append("\n## 4. Configuration Files")
    runtime_files_count = count_lines('runtime_files.txt')
    if runtime_files_count > 0:
        report.append(f"- Files to update: {runtime_files_count}")
        runtime_files_path = AUDIT_DIR / 'runtime_files.txt'
        if runtime_files_path.exists():
            files = runtime_files_path.read_text().strip().split('\n')
            for f in files[:5]:  # Show first 5
                report.append(f"  - `{f}`")
            if len(files) > 5:
                report.append(f"  - ... and {len(files) - 5} more")
    else:
        report.append("- ⚠️  No runtime config files detected")

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
    warnings = []

    if pypi_report:
        critical_deps = [r for r in pypi_report if r.get('status') == 'ERROR']
        if critical_deps:
            blockers.append(f"{len(critical_deps)} dependencies with errors")

        partial_deps = [r for r in pypi_report if r.get('status') == 'PARTIAL']
        if partial_deps:
            warnings.append(f"{len(partial_deps)} dependencies only support 3.10 (verify 3.11 support)")

    if distutils_count > 5:
        blockers.append(f"Heavy distutils usage ({distutils_count} occurrences)")

    if deprecated_count > 10:
        warnings.append(f"{deprecated_count} deprecated imports (auto-fixable)")

    if blockers:
        report.append("**Status**: ⛔ **NO-GO** (blockers found)")
        report.append("\n**Blockers**:")
        for blocker in blockers:
            report.append(f"  - {blocker}")
        report.append("\n**Action**: Resolve blockers before proceeding to Phase 1")
    else:
        report.append("**Status**: ✅ **GO** (proceed to Phase 1)")
        report.append("\n**Recommended actions before Phase 1**:")

        action_num = 1
        if deprecated_count > 0:
            report.append(f"  {action_num}. Fix {deprecated_count} deprecated imports (run `python scripts/fix_deprecated_imports.py`)")
            action_num += 1
        if runtime_files_count > 0:
            report.append(f"  {action_num}. Update {runtime_files_count} configuration files")
            action_num += 1
        if collections_count > 0:
            report.append(f"  {action_num}. Fix {collections_count} collections.abc issues")
            action_num += 1

        report.append(f"  {action_num}. Proceed with Phase 1 (Python 3.11 installation)")

        if warnings:
            report.append("\n**Warnings** (non-blocking):")
            for warning in warnings:
                report.append(f"  - {warning}")

    # 7. Risk assessment
    risk_score = len(blockers) * 10 + len(warnings) * 3 + deprecated_count
    if risk_score == 0:
        risk_level = "VERY LOW"
    elif risk_score < 10:
        risk_level = "LOW"
    elif risk_score < 30:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    report.append(f"\n**Risk Level**: {risk_level}")

    # Write report
    output_file = Path('docs/python310_migration_audit.md')
    output_file.parent.mkdir(exist_ok=True, parents=True)
    output_file.write_text('\n'.join(report))

    print(f"📄 Report generated: {output_file}")
    print("\n" + "="*70)
    print('\n'.join(report[-20:]))  # Print last 20 lines

    # Return exit code based on decision
    return 1 if blockers else 0


if __name__ == '__main__':
    exit(main())
