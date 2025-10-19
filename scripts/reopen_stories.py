#!/usr/bin/env python3
# scripts/reopen_stories.py
import argparse, sys, yaml, pathlib, datetime

def load_yaml(path: pathlib.Path):
    txt = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(txt)
    except Exception as e:
        print("❌ Could not parse planning/stories.yaml as valid YAML.")
        print("   Error:", e)
        print("   Suggestion: run `./.venv/bin/python scripts/fix_stories.py` first if your pipeline has it.")
        sys.exit(2)
    if isinstance(data, dict) and "stories" in data and isinstance(data["stories"], list):
        return data["stories"], "dict_wrapper"
    if isinstance(data, list):
        return data, "list"
    print("❌ YAML is not a top-level list nor a dict with 'stories' key.")
    sys.exit(2)

def save_yaml(path: pathlib.Path, stories, mode: str):
    # backup
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_suffix(path.suffix + f".bak.{ts}")
    backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    if mode == "dict_wrapper":
        data = {"stories": stories}
    else:
        data = stories
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"✓ Saved {path} (backup at {backup.name})")

def main():
    ap = argparse.ArgumentParser(description="Reopen stories (status=todo) in planning/stories.yaml")
    ap.add_argument("--file", default="planning/stories.yaml", help="Path to stories.yaml (default: planning/stories.yaml)")
    ap.add_argument("--only", nargs="*", default=None,
                    help="Reopen only specific states (eg: --only blocked fail failed). If not specified, reopens ALL.")
    args = ap.parse_args()

    p = pathlib.Path(args.file)
    if not p.exists():
        print(f"❌ Does not exist {p}")
        sys.exit(1)

    stories, mode = load_yaml(p)
    if not isinstance(stories, list):
        print("❌ Unexpected format in stories.")
        sys.exit(2)

    before = {s.get("id","?"): s.get("status") for s in stories if isinstance(s, dict)}
    changed = 0
    target_states = set([s.lower() for s in (args.only or [])])

    for s in stories:
        if not isinstance(s, dict):
            continue
        cur = (s.get("status") or "").lower()
        if args.only:
            if cur in target_states:
                s["status"] = "todo"
                changed += 1
        else:
            # reopen all
            s["status"] = "todo"
            changed += 1

    save_yaml(p, stories, mode)

    after = {s.get("id","?"): s.get("status") for s in stories if isinstance(s, dict)}
    print(f"Reopened: {changed} stories.")
    # small summary
    from collections import Counter
    print("Previous status:", Counter(before.values()))
    print("Current status:", Counter(after.values()))

if __name__ == "__main__":
    main()
