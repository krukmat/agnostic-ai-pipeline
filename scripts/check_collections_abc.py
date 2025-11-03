#!/usr/bin/env python3
"""
Detecta uso de collections deprecated.
Python 3.10+ requiere importar de collections.abc en lugar de collections.

Usage:
    python scripts/check_collections_abc.py
"""
import ast
import sys
from pathlib import Path

DEPRECATED_COLLECTIONS = {
    'Callable', 'Iterable', 'Iterator', 'Mapping', 'MutableMapping',
    'Sequence', 'MutableSequence', 'Set', 'MutableSet', 'Collection',
    'Container', 'ItemsView', 'KeysView', 'ValuesView', 'Reversible',
    'Generator', 'AsyncIterable', 'AsyncIterator', 'AsyncGenerator',
    'Coroutine', 'Awaitable'
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
    except SyntaxError as e:
        print(f"⚠️  Syntax error in {file_path}: {e}", file=sys.stderr)
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
        print("\nRun 'python scripts/fix_deprecated_imports.py' to auto-fix")
        return 1
    else:
        print("✅ No deprecated collections imports")
        return 0


if __name__ == '__main__':
    sys.exit(main())
