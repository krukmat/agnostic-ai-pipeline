from __future__ import annotations

import json
import os
import sys
from typing import Dict, List

from google import genai
from google.genai.types import HttpOptions


def chat(
    messages: List[Dict],
    model: str | None = None,
    project_id: str | None = None,
    location: str | None = None,
    temperature: float = 0.2,
    max_output_tokens: int = 2048,
    **_,
) -> str:
    client = genai.Client(
        http_options=HttpOptions(api_version="v1"),
        vertexai=True,
        project=project_id or os.environ.get("GCP_PROJECT"),
        location=location or os.environ.get("VERTEX_LOCATION", "us-central1"),
    )
    response = client.models.generate_content(
        model=model or os.environ.get("VERTEX_MODEL", "gemini-2.5-flash"),
        contents=messages,
        config={
            "temperature": float(temperature),
            "max_output_tokens": int(max_output_tokens),
        },
    )
    return response.text or ""


if __name__ == "__main__":
    payload = json.load(sys.stdin)
    sys.stdout.write(chat(**payload))
