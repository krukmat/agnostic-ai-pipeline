import json
import os
import subprocess
import sys

import pytest


def test_vertex_cli_smoke():
    if not os.environ.get("GCP_PROJECT"):
        pytest.skip("GCP_PROJECT env not set; skipping Vertex smoke test")

    payload = {
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": "Say OK"}]},
        ]
    }
    proc = subprocess.run(
        [sys.executable, "scripts/providers/vertex_cli.py"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
    )
    assert isinstance(proc.stdout, str)
    assert proc.stdout.strip() != ""
