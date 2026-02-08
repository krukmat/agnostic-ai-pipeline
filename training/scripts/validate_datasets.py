#!/usr/bin/env python3
"""Valida estructura mínima de datasets sintéticos JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED = ["instruction", "input", "output", "role", "metadata"]


def validate_file(path: Path) -> tuple[int, int]:
    total = 0
    invalid = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        total += 1
        try:
            row = json.loads(line)
        except Exception:
            invalid += 1
            continue
        for key in REQUIRED:
            if key not in row:
                invalid += 1
                break
    return total, invalid


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("training/datasets"))
    args = parser.parse_args()

    role_dir = args.output_dir / args.role
    if not role_dir.exists():
        print(json.dumps({"ok": False, "reason": "role_dir_not_found", "role": args.role}, ensure_ascii=False))
        return 1

    files = sorted(role_dir.glob("*.jsonl"))
    if not files:
        print(json.dumps({"ok": False, "reason": "no_jsonl_files", "role": args.role}, ensure_ascii=False))
        return 1

    total = 0
    invalid = 0
    for f in files:
        t, i = validate_file(f)
        total += t
        invalid += i

    payload = {
        "ok": invalid == 0,
        "role": args.role,
        "files": len(files),
        "total_rows": total,
        "invalid_rows": invalid,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
