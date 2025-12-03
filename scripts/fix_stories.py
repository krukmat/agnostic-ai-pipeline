import re, sys, yaml, pathlib

P = pathlib.Path("planning/stories.yaml")

def uncomment_structured(lines):
    out=[]
    for line in lines:
        ls=line.lstrip()
        if ls.startswith('#'):
            body = ls[1:]
            # Only uncomment if it looks like YAML (key: or item "- ...")
            if body.lstrip().startswith('-') or re.match(r'\s*[A-Za-z0-9_]+\s*:', body):
                indent = line[:len(line)-len(ls)]
                out.append(indent + body.lstrip())
                continue
            # discard plain comments
            continue
        out.append(line)
    return out

def remove_fences(txt:str)->str:
    # remove ``` and ```yaml
    txt = re.sub(r'^\s*```(?:yaml|yml)?\s*', '', txt, flags=re.MULTILINE)
    txt = re.sub(r'\s*```\s*$', '', txt, flags=re.MULTILINE)
    return txt

def fix_acceptance_inline(txt:str)->str:
    lines = txt.splitlines()
    out=[]
    for line in lines:
        # Case 1: "acceptance: - item" => block + item
        m = re.match(r'^(\s*)acceptance:\s*-\s*(.+)\s*$', line)
        if m:
            ind, first = m.group(1), m.group(2).strip()
            out.append(f"{ind}acceptance:")
            out.append(f"{ind}  - {first}")
            continue
        # Case 2: "acceptance: a; b; c" => list of items
        m2 = re.match(r'^(\s*)acceptance:\s*(.+)\s*$', line)
        if m2:
            ind, val = m2.group(1), m2.group(2).strip()
            # If already flow-style [a, b] or literal don't touch
            if val and not val.startswith('[') and not val.startswith('|') and not val.startswith('>') and not val.startswith('&') and not val.startswith('*') and not val.startswith('-'):
                parts = [p.strip(' -•\t ') for p in re.split(r';|\u2022|\u00b7|\|', val) if p.strip()]
                if parts:
                    out.append(f"{ind}acceptance:")
                    for p in parts:
                        out.append(f"{ind}  - {p}")
                    continue
        out.append(line)
    return "\n".join(out)

def sanitize_acceptance_bullets(txt: str) -> str:
    """Sanitize acceptance list items to avoid YAML parse issues (colons/quotes in plain scalars)."""
    lines = txt.splitlines()
    out = []
    in_acc = False
    acc_indent = None

    for line in lines:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if stripped.startswith("acceptance:"):
            in_acc = True
            acc_indent = indent
            out.append(line)
            continue

        # exit acceptance block when indentation decreases
        if in_acc and indent <= (acc_indent or 0) and stripped and not stripped.startswith("- "):
            in_acc = False

        if in_acc and stripped.startswith("- "):
            content = stripped[2:]
            # Replace patterns like "foo": "bar" -> foo=bar
            content = re.sub(r'"([^"]+)"\s*:\s*"([^"]+)"', r'\1=\2', content)
            # Drop remaining double quotes
            content = content.replace('"', "")
            # Avoid standalone colon in plain scalars
            content = content.replace(": ", " - ")
            out.append(f"{' ' * indent}- {content.strip()}")
            continue

        out.append(line)
    return "\n".join(out)

def repair_broken_id_lines(txt: str) -> str:
    """Fix malformed id lines like '- id - S2' -> '- id: S2'."""
    out = []
    for line in txt.splitlines():
        m = re.match(r'^(\s*)-+\s*id\s*[-–]\s*(\S+)\s*$', line)
        if m:
            indent, sid = m.group(1), m.group(2)
            out.append(f"{indent}- id: {sid}")
        else:
            out.append(line)
    return "\n".join(out)
def ensure_list_top_level(data):
    # Handle cases where model returns {"stories": [...]}
    if isinstance(data, dict) and "stories" in data and isinstance(data["stories"], list):
        return data["stories"]
    if isinstance(data, list):
        return data
    raise SystemExit("stories.yaml is not a top-level list nor contains 'stories:'")

def normalize_status(items):
    fixed=[]
    try:
        from scripts.utils.config_loader import load_config_base
        defaults = load_config_base().get("defaults", {}) if callable(load_config_base) else {}
        default_complexity = defaults.get("complexity", "medium") if isinstance(defaults, dict) else "medium"
    except Exception:
        default_complexity = "medium"

    # Try to import complexity analyzer
    try:
        from scripts.utils.complexity_analyzer import analyze_story_complexity
        use_analyzer = True
    except Exception:
        use_analyzer = False

    for s in items:
        if not isinstance(s, dict):
            continue
        s.setdefault("status", "todo")
        if "complexity" not in s or not s.get("complexity"):
            # Use intelligent analysis if available, otherwise fall back to default
            if use_analyzer:
                auto_complexity = analyze_story_complexity(s, verbose=False)
                print(f"[fix_stories] Missing complexity for story {s.get('id','?')}, auto-classified as {auto_complexity}")
                s["complexity"] = auto_complexity or default_complexity
            else:
                print(f"[fix_stories] Missing complexity for story {s.get('id','?')}, defaulting to {default_complexity}")
                s["complexity"] = default_complexity
        else:
            # Normalize casing
            s["complexity"] = str(s.get("complexity")).lower()
        fixed.append(s)
    return fixed

def main():
    if not P.exists():
        raise SystemExit("planning/stories.yaml does not exist.")

    raw = P.read_text(encoding="utf-8")
    if not raw.strip():
        raise SystemExit("planning/stories.yaml is empty.")

    data = None
    # Fast path: if it already parses, skip text repairs
    try:
        data = yaml.safe_load(raw)
    except Exception:
        data = None

    if data is None:
        # 1) uncomment structured YAML if it came with '#'
        lines = raw.splitlines()
        if all(l.lstrip().startswith('#') or not l.strip() for l in lines):
            lines = uncomment_structured(lines)
        txt = "\n".join(lines)

        # quick repair for malformed id lines "- id - S2" -> "- id: S2"
        txt = re.sub(r"-\s+id\s+-\s+", "- id: ", txt)

        # 2) remove fences
        txt = remove_fences(txt)

        # 3) fix inline 'acceptance'
        txt = fix_acceptance_inline(txt)

        # 4) repair malformed id lines and sanitize acceptance bullets for YAML safety
        txt = repair_broken_id_lines(txt)
        txt = sanitize_acceptance_bullets(txt)

        # 5) try to parse; if fails, show hint
        try:
            data = yaml.safe_load(txt)
        except Exception as e:
            print("YAML parse error:", e)
            print("\n--- CURRENT CONTENT (for diagnostics) ---\n")
            print(txt)
            sys.exit(1)

    items = ensure_list_top_level(data)
    items = normalize_status(items)

    P.write_text(yaml.safe_dump(items, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"✓ stories.yaml normalized with {len(items)} stories. "
          f"All: {sum(1 for s in items if s.get('status')=='todo')}")

if __name__ == "__main__":
    main()
