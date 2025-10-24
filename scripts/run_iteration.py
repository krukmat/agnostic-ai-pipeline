from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

from common import ensure_dirs, PLANNING, PROJECT, ROOT


def run_command(cmd: list[str], env: Dict[str, str] | None = None) -> int:
    """Run a command in the repository root and stream output."""
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    print(f"[iteration] run: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT, env=merged_env)
    if result.returncode != 0:
        print(f"[iteration] command failed (rc={result.returncode}) -> {' '.join(cmd)}")
    return result.returncode


def snapshot_iteration(iteration_name: str, concept: str, loops: int, allow_no_tests: bool) -> None:
    """Persist a snapshot of planning and project artifacts for the iteration."""
    iterations_dir = ROOT / "artifacts" / "iterations"
    iteration_dir = iterations_dir / iteration_name
    iteration_dir.mkdir(parents=True, exist_ok=True)

    summary = build_summary(concept, loops, allow_no_tests)
    (iteration_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Copy planning and project trees for traceability
    copytree_safe(PLANNING, iteration_dir / "planning")
    copytree_safe(PROJECT, iteration_dir / "project")

    # Optional: compressed archive for compact storage
    archive_path = iterations_dir / f"{iteration_name}.zip"
    if archive_path.exists():
        archive_path.unlink()
    shutil.make_archive(str(archive_path.with_suffix("")), "zip", iteration_dir)
    print(f"[iteration] Snapshot stored under artifacts/iterations/{iteration_name}")


def copytree_safe(src: Path, dest: Path) -> None:
    if not src.exists():
        return
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def build_summary(concept: str, loops: int, allow_no_tests: bool) -> Dict[str, Any]:
    stories_file = PLANNING / "stories.yaml"
    try:
        import yaml  # Local import to avoid hard dependency when not needed

        stories = []
        if stories_file.exists():
            stories = yaml.safe_load(stories_file.read_text(encoding="utf-8")) or []
            if isinstance(stories, dict) and "stories" in stories:
                stories = stories["stories"]
        if not isinstance(stories, list):
            stories = []
    except Exception as exc:
        print(f"[iteration] Warning: could not parse stories.yaml ({exc})")
        stories = []

    counts: Dict[str, int] = {}
    done, blocked, in_progress = [], [], []
    for story in stories:
        status = str(story.get("status", "unknown")).lower()
        counts[status] = counts.get(status, 0) + 1
        sid = story.get("id")
        if status == "done":
            done.append(sid)
        elif status.startswith("blocked"):
            blocked.append(sid)
        elif status in {"in_review", "todo"}:
            in_progress.append(sid)

    return {
        "concept": concept,
        "timestamp": dt.datetime.utcnow().isoformat() + "Z",
        "loops_requested": loops,
        "allow_no_tests": allow_no_tests,
        "story_status_counts": counts,
        "stories_done": done,
        "stories_blocked": blocked,
        "stories_pending": in_progress,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a full BA→Architect→Dev→QA iteration pipeline.")
    parser.add_argument("--concept", help="Business concept to feed into BA/Architect", default="")
    parser.add_argument(
        "--iteration-name",
        help="Name for the iteration snapshot (default: iteration-YYYYmmdd-HHMMSS)",
        default="",
    )
    parser.add_argument(
        "--loops",
        type=int,
        default=None,
        help="How many automatic Dev→QA loops to execute (passed to make loop as MAX_LOOPS)",
    )
    parser.add_argument(
        "--allow-no-tests",
        action="store_true",
        help="Forward ALLOW_NO_TESTS=1 to the QA stage during make loop",
    )
    parser.add_argument(
        "--skip-ba",
        action="store_true",
        help="Skip BA step (useful when requirements already exist for refinement iterations)",
    )
    parser.add_argument(
        "--skip-plan",
        action="store_true",
        help="Skip architect planning step (useful for pure execution iterations)",
    )
    parser.add_argument(
        "--skip-po",
        action="store_true",
        help="Skip Product Owner validation step",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    ensure_dirs()

    args = parse_args(argv)

    env = os.environ
    concept = args.concept or env.get("CONCEPT", "").strip()

    iteration_name = args.iteration_name or env.get("ITERATION_NAME", "") or dt.datetime.utcnow().strftime("iteration-%Y%m%d-%H%M%S")

    loops_option = args.loops if args.loops is not None else int(env.get("LOOPS", "1"))
    allow_no_tests = args.allow_no_tests or env.get("ALLOW_NO_TESTS", "0") == "1"
    skip_ba = args.skip_ba or env.get("SKIP_BA", "0") == "1"
    skip_po = args.skip_po or env.get("SKIP_PO", "0") == "1"
    skip_plan = args.skip_plan or env.get("SKIP_PLAN", "0") == "1"

    if concept:
        print(f"[iteration] Using concept: {concept}")

    if not skip_ba:
        if not concept:
            print("[iteration] ERROR: provide --concept when BA step is enabled")
            return 1
        rc = run_command(["make", "ba"], env={"CONCEPT": concept})
        if rc != 0:
            return rc
    else:
        print("[iteration] Skipping BA step as requested")

    if not skip_po:
        po_env = {"CONCEPT": concept} if concept else None
        rc = run_command(["make", "po"], env=po_env)
        if rc != 0:
            return rc
    else:
        print("[iteration] Skipping Product Owner step as requested")

    if not skip_plan:
        plan_env = {"CONCEPT": concept} if concept else None
        rc = run_command(["make", "plan"], env=plan_env)
        if rc != 0:
            return rc
    else:
        print("[iteration] Skipping Architect planning step as requested")

    loop_env = {
        "MAX_LOOPS": str(max(1, loops_option)),
        "ALLOW_NO_TESTS": "1" if allow_no_tests else "0",
    }
    if concept:
        loop_env["CONCEPT"] = concept
    rc = run_command(["make", "loop"], env=loop_env)
    if rc != 0:
        print("[iteration] make loop returned non-zero exit code")

    snapshot_iteration(iteration_name, concept, loops_option, allow_no_tests)
    print(f"[iteration] Completed iteration '{iteration_name}'")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
