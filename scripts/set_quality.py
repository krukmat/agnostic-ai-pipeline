# scripts/set_quality.py
from __future__ import annotations
import argparse, sys, pathlib, yaml

PRESETS = {
    "low":    {"temperature": 0.05, "top_p": 0.90, "max_tokens": 1536},
    "normal": {"temperature": 0.20, "top_p": 0.95, "max_tokens": 2048},
    "high":   {"temperature": 0.40, "top_p": 0.95, "max_tokens": 4096},
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True, choices=PRESETS.keys())
    ap.add_argument("--role", required=False, help="architect | dev | qa (opcional). Si no se pasa, aplica a todos.")
    args = ap.parse_args()

    root = pathlib.Path(__file__).resolve().parents[1]
    cfg_path = root / "config.yaml"
    if not cfg_path.exists():
        sys.exit("config.yaml no encontrado")

    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    roles = cfg.setdefault("roles", {})

    target_roles = [args.role] if args.role else (list(roles.keys()) or ["ba", "architect", "dev", "qa"])
    # asegura estructura si faltan
    for r in target_roles:
        roles.setdefault(r, {})

    preset = PRESETS[args.profile]
    for r in target_roles:
        roles[r].update(preset)

    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"✔ quality={args.profile} aplicado a: {', '.join(target_roles)}")

if __name__ == "__main__":
    main()
