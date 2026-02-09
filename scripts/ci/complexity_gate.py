#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


RANK_SCORE = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}
BLOCK_RE = re.compile(r"^\s*([A-Z])\s+(\d+):(\d+)\s+(.+?)\s+-\s+([A-F])\s+\((\d+)\)\s*$")


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=check)


def _changed_python_files(base_ref: str, head_ref: str) -> list[str]:
    cp = _run(["git", "diff", "--name-only", f"{base_ref}...{head_ref}", "--", "*.py"], check=False)
    if cp.returncode != 0:
        raise RuntimeError(f"git diff failed: {cp.stderr.strip()}")
    return sorted({line.strip() for line in cp.stdout.splitlines() if line.strip()})


def _file_content_at_ref(ref: str, file_path: str) -> str | None:
    cp = _run(["git", "show", f"{ref}:{file_path}"], check=False)
    if cp.returncode != 0:
        return None
    return cp.stdout


def _run_radon_s(paths: list[str], *, cwd: Path) -> str:
    if not paths:
        return ""
    cp = _run([sys.executable, "-m", "radon", "cc", "-s", *paths], check=False)
    if cp.returncode != 0:
        raise RuntimeError(f"radon failed: {cp.stderr.strip()}\n{cp.stdout}")
    return cp.stdout


def _parse_radon_output(output: str) -> dict[str, dict[str, dict[str, Any]]]:
    parsed: dict[str, dict[str, dict[str, Any]]] = {}
    current_file: str | None = None

    for raw_line in output.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.endswith(".py"):
            current_file = stripped
            parsed.setdefault(current_file, {})
            continue

        m = BLOCK_RE.match(line)
        if not m or not current_file:
            continue

        kind, lineno, col, name, rank, score = m.groups()
        key = f"{kind}:{name}"
        parsed[current_file][key] = {
            "file": current_file,
            "kind": kind,
            "name": name,
            "rank": rank,
            "score": int(score),
            "lineno": int(lineno),
            "col": int(col),
        }
    return parsed


def _load_exceptions(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    allow_d = data.get("allow_d", []) if isinstance(data, dict) else []
    return [x for x in allow_d if isinstance(x, dict)]


def _matches(value: str, pattern: str | None) -> bool:
    if not pattern or pattern == "*":
        return True
    return value == pattern


def _has_d_exception(exceptions: list[dict[str, str]], block: dict[str, Any]) -> bool:
    for exc in exceptions:
        if (
            _matches(block["file"], exc.get("file"))
            and _matches(block["kind"], exc.get("kind"))
            and _matches(block["name"], exc.get("name"))
        ):
            return True
    return False


def _collect_base_blocks(base_ref: str, files: list[str]) -> dict[str, dict[str, dict[str, Any]]]:
    with tempfile.TemporaryDirectory(prefix="complexity-gate-") as tmp:
        tmpdir = Path(tmp)
        existing_rel_files: list[str] = []

        for file_path in files:
            content = _file_content_at_ref(base_ref, file_path)
            if content is None:
                continue
            dst = tmpdir / file_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(content, encoding="utf-8")
            existing_rel_files.append(file_path)

        if not existing_rel_files:
            return {}

        old_cwd = Path.cwd()
        try:
            # run radon in temp tree so file paths remain relative
            import os

            os.chdir(tmpdir)
            output = _run_radon_s(existing_rel_files, cwd=tmpdir)
        finally:
            os.chdir(old_cwd)

    return _parse_radon_output(output)


def _collect_head_blocks(files: list[str]) -> dict[str, dict[str, dict[str, Any]]]:
    existing = [f for f in files if Path(f).exists()]
    if not existing:
        return {}
    output = _run_radon_s(existing, cwd=Path.cwd())
    return _parse_radon_output(output)


def main() -> int:
    parser = argparse.ArgumentParser(description="Complexity gate for changed Python files")
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--head-ref", required=True)
    parser.add_argument(
        "--exceptions-file",
        default=".github/complexity_exceptions.json",
        help="JSON file with allowed D exceptions",
    )
    args = parser.parse_args()

    changed_files = _changed_python_files(args.base_ref, args.head_ref)
    if not changed_files:
        print("[complexity-gate] No changed Python files. PASS")
        return 0

    print(f"[complexity-gate] Changed Python files: {len(changed_files)}")
    for f in changed_files:
        print(f"  - {f}")

    base_blocks = _collect_base_blocks(args.base_ref, changed_files)
    head_blocks = _collect_head_blocks(changed_files)
    exceptions = _load_exceptions(Path(args.exceptions_file))

    hard_fail: list[dict[str, Any]] = []
    d_fail: list[dict[str, Any]] = []

    for file_path, blocks in head_blocks.items():
        old_blocks = base_blocks.get(file_path, {})
        for key, block in blocks.items():
            rank = block["rank"]
            if RANK_SCORE.get(rank, 0) < RANK_SCORE["D"]:
                continue

            old_rank = old_blocks.get(key, {}).get("rank")
            if old_rank and RANK_SCORE[rank] <= RANK_SCORE.get(old_rank, 0):
                continue  # unchanged or improved

            if rank in {"E", "F"}:
                hard_fail.append(block)
            elif rank == "D" and not _has_d_exception(exceptions, block):
                d_fail.append(block)

    if not hard_fail and not d_fail:
        print("[complexity-gate] PASS: no new/worsened D/E/F violations")
        return 0

    print("\n[complexity-gate] FAIL")
    if hard_fail:
        print("\n  New/worsened E/F blocks (blocked):")
        for b in hard_fail:
            print(f"   - {b['file']}::{b['name']} [{b['kind']}] rank={b['rank']} cc={b['score']}")

    if d_fail:
        print("\n  New/worsened D blocks without approved exception:")
        for b in d_fail:
            print(f"   - {b['file']}::{b['name']} [{b['kind']}] rank={b['rank']} cc={b['score']}")
        print("\n  Add a documented exception in .github/complexity_exceptions.json with issue + reason.")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
