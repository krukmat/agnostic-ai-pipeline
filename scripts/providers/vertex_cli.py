from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Dict, List

import httpx

# Import logger for debugging
try:
    from logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(f"Missing required env: {name}")
    return value


def _gcloud_token() -> str:
    token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
    if not token:
        raise RuntimeError("Empty access token from gcloud")
    return token


def _to_vertex_contents(messages: List[Dict]) -> List[Dict]:
    contents: List[Dict] = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", [])
        vertex_role = "user" if role in ("user", "system") else "model"
        parts = [{"text": part.get("text", "")} for part in content if part.get("type") == "text"]
        if parts:
            contents.append({"role": vertex_role, "parts": parts})
    return contents


def _call_generate_content(
    project_id: str,
    location: str,
    model: str,
    contents: List[Dict],
    temperature: float,
    max_tokens: int,
    timeout: float = 120.0,
) -> str:
    url = (
        f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/"
        f"locations/{location}/publishers/google/models/{model}:generateContent"
    )
    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    headers = {
        "Authorization": f"Bearer {_gcloud_token()}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    # Task: fix-vertex-cli-truncation - debug logging
    candidates = data.get("candidates", [])
    if not candidates:
        logger.warning("[VERTEX_CLI] No candidates in response")
        return ""

    candidate = candidates[0]
    finish_reason = candidate.get("finishReason")
    safety_ratings = candidate.get("safetyRatings", [])

    logger.debug(f"[VERTEX_CLI] finishReason: {finish_reason}")
    logger.debug(f"[VERTEX_CLI] safetyRatings: {safety_ratings}")

    # Task: fix-vertex-cli-truncation - concatenate all text parts instead of returning first
    parts = candidate.get("content", {}).get("parts", [])
    logger.debug(f"[VERTEX_CLI] Parts count: {len(parts)}")

    text_parts = []
    for idx, part in enumerate(parts):
        if "text" in part and part["text"]:
            part_len = len(part["text"])
            logger.debug(f"[VERTEX_CLI] Part {idx} length: {part_len}")
            text_parts.append(part["text"])

    result = "".join(text_parts) if text_parts else ""
    logger.debug(f"[VERTEX_CLI] Total result length: {len(result)}")
    return result


def _call_openai_compat(
    project_id: str,
    location: str,
    model: str,
    messages: List[Dict],
    temperature: float,
    max_tokens: int,
    timeout: float = 120.0,
) -> str:
    url = (
        f"https://{location}-aiplatform.googleapis.com/v1beta/projects/{project_id}/"
        f"locations/{location}/endpoints/openapi/chat/completions"
    )
    payload = {
        "model": f"google/{model}" if not model.startswith("google/") else model,
        "messages": messages,
        "temperature": temperature,
        "max_output_tokens": max_tokens,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {_gcloud_token()}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message", {})
    content = message.get("content") or []
    segments = []
    for part in content:
        if part.get("type") == "text" and part.get("text"):
            segments.append(part["text"])
    return "\n".join(segments).strip()


def chat(
    messages: List[Dict],
    model: str | None = None,
    project_id: str | None = None,
    location: str | None = None,
    temperature: float = 0.2,
    max_output_tokens: int = 2048,
    **_,
) -> str:
    resolved_project = project_id or os.environ.get("GCP_PROJECT") or _env("GCP_PROJECT")
    resolved_location = location or os.environ.get("VERTEX_LOCATION", "us-central1")
    resolved_model = model or os.environ.get("VERTEX_MODEL", "gemini-2.5-flash")
    use_openai = os.environ.get("USE_OPENAI_COMPAT", "0") == "1"

    if use_openai:
        return _call_openai_compat(
            resolved_project,
            resolved_location,
            resolved_model,
            messages,
            float(temperature),
            int(max_output_tokens),
        )

    contents = _to_vertex_contents(messages)
    return _call_generate_content(
        resolved_project,
        resolved_location,
        resolved_model,
        contents,
        float(temperature),
        int(max_output_tokens),
    )


if __name__ == "__main__":
    payload = json.load(sys.stdin)
    output = chat(**payload)
    sys.stdout.write(output)
