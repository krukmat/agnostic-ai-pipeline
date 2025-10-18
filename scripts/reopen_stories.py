#!/usr/bin/env python3
# scripts/reopen_stories.py
import argparse, sys, yaml, pathlib, datetime

def load_yaml(path: pathlib.Path):
    txt = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(txt)
    except Exception as e:
        print("❌ No pude parsear planning/stories.yaml como YAML válido.")
        print("   Error:", e)
        print("   Sugerencia: ejecuta primero `./.venv/bin/python scripts/fix_stories.py` si tu pipeline lo tiene.")
        sys.exit(2)
    if isinstance(data, dict) and "stories" in data and isinstance(data["stories"], list):
        return data["stories"], "dict_wrapper"
    if isinstance(data, list):
        return data, "list"
    print("❌ El YAML no es una lista top-level ni un dict con clave 'stories'.")
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
    print(f"✓ Guardado {path} (backup en {backup.name})")

def main():
    ap = argparse.ArgumentParser(description="Reabrir stories (status=todo) en planning/stories.yaml")
    ap.add_argument("--file", default="planning/stories.yaml", help="Ruta del stories.yaml (por defecto: planning/stories.yaml)")
    ap.add_argument("--only", nargs="*", default=None,
                    help="Reabrir solo estados específicos (ej: --only blocked fail failed). Si no se indica, reabre TODAS.")
    args = ap.parse_args()

    p = pathlib.Path(args.file)
    if not p.exists():
        print(f"❌ No existe {p}")
        sys.exit(1)

    stories, mode = load_yaml(p)
    if not isinstance(stories, list):
        print("❌ Formato inesperado en stories.")
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
            # reabrir todas
            s["status"] = "todo"
            changed += 1

    save_yaml(p, stories, mode)

    after = {s.get("id","?"): s.get("status") for s in stories if isinstance(s, dict)}
    print(f"Reabiertas: {changed} historias.")
    # pequeño resumen
    from collections import Counter
    print("Estado previo:", Counter(before.values()))
    print("Estado actual:", Counter(after.values()))

if __name__ == "__main__":
    main()

