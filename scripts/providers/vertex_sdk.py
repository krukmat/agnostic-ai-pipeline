from __future__ import annotations

import json
import os
import sys
from typing import Dict, List

from google import genai
from google.genai.types import HttpOptions

# Import logger for debugging
try:
    from logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


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

    # Transform messages to the format expected by the SDK
    transformed_contents = []
    for msg in messages:
        if msg.get("role") == "user" or msg.get("role") == "system":
            content = msg.get("content", [])
            if isinstance(content, list) and content and content[0].get("type") == "text":
                transformed_contents.append(content[0].get("text", ""))

    response = client.models.generate_content(
        model=model or os.environ.get("VERTEX_MODEL", "gemini-2.5-flash"),
        contents=transformed_contents,
        config={
            "temperature": float(temperature),
            "max_output_tokens": int(max_output_tokens),
        },
    )

    # Task: Fix vertex_sdk - Extract complete text from response and add debugging
    # response.text can be truncated, so we need to extract from candidates
    try:
        # Debug: Log raw response structure
        logger.debug(f"[VERTEX_SDK] Response type: {type(response)}")
        logger.debug(f"[VERTEX_SDK] Has text attr: {hasattr(response, 'text')}")
        logger.debug(f"[VERTEX_SDK] Has candidates attr: {hasattr(response, 'candidates')}")

        if hasattr(response, 'text'):
            text_len = len(response.text) if response.text else 0
            logger.debug(f"[VERTEX_SDK] response.text length: {text_len}")

        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            logger.debug(f"[VERTEX_SDK] Candidate type: {type(candidate)}")
            logger.debug(f"[VERTEX_SDK] Candidate has content: {hasattr(candidate, 'content')}")

            if hasattr(candidate, 'content') and candidate.content:
                # Extract all text parts from the content
                text_parts = []
                if hasattr(candidate.content, 'parts'):
                    logger.debug(f"[VERTEX_SDK] Parts count: {len(candidate.content.parts)}")
                    for idx, part in enumerate(candidate.content.parts):
                        if hasattr(part, 'text') and part.text:
                            part_len = len(part.text)
                            logger.debug(f"[VERTEX_SDK] Part {idx} length: {part_len}")
                            text_parts.append(part.text)
                if text_parts:
                    full_text = "".join(text_parts)
                    logger.debug(f"[VERTEX_SDK] Returning joined parts, total length: {len(full_text)}")
                    return full_text

        # Fallback to response.text if available
        if hasattr(response, 'text') and response.text:
            logger.debug(f"[VERTEX_SDK] Falling back to response.text")
            return response.text

        logger.debug(f"[VERTEX_SDK] Returning empty string")
        return ""
    except Exception as e:
        logger.error(f"[VERTEX_SDK] Exception extracting text: {e}")
        # If extraction fails, fallback to response.text
        return response.text or ""


if __name__ == "__main__":
    payload = json.load(sys.stdin)
    sys.stdout.write(chat(**payload))
