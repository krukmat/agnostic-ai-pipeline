import argparse, yaml, pathlib, os


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", required=True, choices=["ba","architect","dev","qa"])
    parser.add_argument(
        "--provider",
        required=False,
        choices=["ollama", "openai", "codex_cli", "vertex_cli", "vertex_sdk", "claude_cli"],
    )
    parser.add_argument("--model", required=False)
    args = parser.parse_args(argv)

    root = pathlib.Path(__file__).resolve().parents[1]
    cfg_p = pathlib.Path(os.environ.get("CONFIG_PATH", root / "config.yaml"))

    cfg = yaml.safe_load(cfg_p.read_text(encoding="utf-8"))
    role_cfg = cfg["roles"][args.role]
    if args.provider:
        role_cfg["provider"] = args.provider
    if args.model:
        role_cfg["model"] = args.model
    cfg_p.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"updated {args.role}: {role_cfg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
