from __future__ import annotations
import os, re, asyncio, pathlib
from common import load_config, ensure_dirs, PLANNING, ROOT
from llm import LLMClient

ARCH_PROMPT = (ROOT/"prompts"/"architect.md").read_text(encoding="utf-8")

async def main():
    ensure_dirs()
    cfg = load_config()
    concept = os.environ.get("CONCEPT","").strip()
    if not concept:
        raise SystemExit('Set CONCEPT="..."')

    role = cfg["roles"]["architect"]
    prov = role.get("provider","ollama")
    base = cfg["providers"]["ollama"].get("base_url","http://localhost:11434") if prov=="ollama" else cfg["providers"].get("openai",{}).get("base_url")

    client = LLMClient(prov, role["model"], role.get("temperature",0.2), role.get("max_tokens",2048), base)
    text = await client.chat(system=ARCH_PROMPT, user=f"CONCEPT:\n{concept}\n\nFollow the exact output format.")

    def grab(tag, label):
        m = re.search(rf"```{tag}\s+{label}\s*([\s\S]*?)```", text)
        return m.group(1).strip() if m else ""

    (PLANNING/"prd.yaml").write_text(grab("yaml","PRD"), encoding="utf-8")
    (PLANNING/"architecture.yaml").write_text(grab("yaml","ARCH"), encoding="utf-8")
    (PLANNING/"epics.yaml").write_text(grab("yaml","EPICS"), encoding="utf-8")
    (PLANNING/"stories.yaml").write_text(grab("yaml","STORIES"), encoding="utf-8")
    (PLANNING/"tasks.csv").write_text(grab("csv","TASKS"), encoding="utf-8")
    print("✓ planning written under planning/")

if __name__ == "__main__":
    asyncio.run(main())
