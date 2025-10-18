import re, sys, yaml, pathlib

P = pathlib.Path("planning/stories.yaml")

def uncomment_structured(lines):
    out=[]
    for line in lines:
        ls=line.lstrip()
        if ls.startswith('#'):
            body = ls[1:]
            # Solo descomenta si parece YAML (clave:, o item "- ...")
            if body.lstrip().startswith('-') or re.match(r'\s*[A-Za-z0-9_]+\s*:', body):
                indent = line[:len(line)-len(ls)]
                out.append(indent + body.lstrip())
                continue
            # descarta comentarios planos
            continue
        out.append(line)
    return out

def remove_fences(txt:str)->str:
    # elimina ``` y ```yaml
    txt = re.sub(r'^\s*```(?:yaml|yml)?\s*', '', txt, flags=re.MULTILINE)
    txt = re.sub(r'\s*```\s*$', '', txt, flags=re.MULTILINE)
    return txt

def fix_acceptance_inline(txt:str)->str:
    lines = txt.splitlines()
    out=[]
    for line in lines:
        # Caso 1: "acceptance: - algo"  => bloque + item
        m = re.match(r'^(\s*)acceptance:\s*-\s*(.+)\s*$', line)
        if m:
            ind, first = m.group(1), m.group(2).strip()
            out.append(f"{ind}acceptance:")
            out.append(f"{ind}  - {first}")
            continue
        # Caso 2: "acceptance: a; b; c" => lista de items
        m2 = re.match(r'^(\s*)acceptance:\s*(.+)\s*$', line)
        if m2:
            ind, val = m2.group(1), m2.group(2).strip()
            # Si ya es flow-style [a, b] o literal no tocar
            if val and not val.startswith('[') and not val.startswith('|') and not val.startswith('>') and not val.startswith('&') and not val.startswith('*') and not val.startswith('-'):
                parts = [p.strip(' -•\t ') for p in re.split(r';|\u2022|\u00b7|\|', val) if p.strip()]
                if parts:
                    out.append(f"{ind}acceptance:")
                    for p in parts:
                        out.append(f"{ind}  - {p}")
                    continue
        out.append(line)
    return "\n".join(out)

def ensure_list_top_level(data):
    # Admite casos donde el modelo devuelve {"stories": [...]}
    if isinstance(data, dict) and "stories" in data and isinstance(data["stories"], list):
        return data["stories"]
    if isinstance(data, list):
        return data
    raise SystemExit("stories.yaml no es una lista top-level ni contiene 'stories:'")

def normalize_status(items):
    fixed=[]
    for s in items:
        if not isinstance(s, dict): 
            continue
        s.setdefault("status", "todo")
        fixed.append(s)
    return fixed

def main():
    if not P.exists():
        raise SystemExit("planning/stories.yaml no existe.")

    raw = P.read_text(encoding="utf-8")
    if not raw.strip():
        raise SystemExit("planning/stories.yaml vacío.")

    # 1) descomentar YAML estructurado si vino con '#'
    lines = raw.splitlines()
    if all(l.lstrip().startswith('#') or not l.strip() for l in lines):
        lines = uncomment_structured(lines)
    txt = "\n".join(lines)

    # 2) quitar fences
    txt = remove_fences(txt)

    # 3) arreglar 'acceptance' en línea
    txt = fix_acceptance_inline(txt)

    # 4) intentar parsear; si falla, mostrar hint
    try:
        data = yaml.safe_load(txt)
    except Exception as e:
        print("YAML parse error:", e)
        print("\n--- CONTENIDO ACTUAL (para diagnóstico) ---\n")
        print(txt)
        sys.exit(1)

    items = ensure_list_top_level(data)
    items = normalize_status(items)

    P.write_text(yaml.safe_dump(items, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"✓ stories.yaml normalizado con {len(items)} historias. "
          f"Todos: {sum(1 for s in items if s.get('status')=='todo')}")
    
if __name__ == "__main__":
    main()
