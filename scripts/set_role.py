import argparse, yaml, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
cfg_p = ROOT/"config.yaml"

ap = argparse.ArgumentParser()
ap.add_argument("--role", required=True, choices=["ba","architect","dev","qa"])
ap.add_argument("--provider", required=False, choices=["ollama","openai"])
ap.add_argument("--model", required=False)
args = ap.parse_args()

cfg = yaml.safe_load(cfg_p.read_text(encoding="utf-8"))
role = cfg["roles"][args.role]
if args.provider: role["provider"] = args.provider
if args.model: role["model"] = args.model
cfg_p.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
print(f"updated {args.role}: {role}")
