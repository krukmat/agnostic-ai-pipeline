from __future__ import annotations
import os, re, asyncio, pathlib
from common import load_config, ensure_dirs, PLANNING, ROOT
from llm import LLMClient

BA_PROMPT = (ROOT/"prompts"/"ba.md").read_text(encoding="utf-8")

async def main():
    ensure_dirs()
    cfg = load_config()
    concept = os.environ.get("CONCEPT","").strip()
    if not concept:
        raise SystemExit('Set CONCEPT="..."')

    role = cfg["roles"]["ba"]
    prov = role.get("provider","ollama")
    base = cfg["providers"]["ollama"].get("base_url","http://localhost:11434") if prov=="ollama" else cfg["providers"].get("openai",{}).get("base_url")

    client = LLMClient(prov, role["model"], role.get("temperature",0.2), role.get("max_tokens",2048), base)
    text = await client.chat(system=BA_PROMPT, user=f"CONCEPT:\n{concept}\n\nFollow the exact output format.")

    def grab(tag, label):
        m = re.search(rf"```{tag}\s+{label}\s*([\s\S]*?)```", text)
        return m.group(1).strip() if m else ""

    (PLANNING/"requirements.yaml").write_text(grab("yaml","REQUIREMENTS"), encoding="utf-8")
    print("✓ requirements.yaml written under planning/")

if __name__ == "__main__":
    asyncio.run(main())
