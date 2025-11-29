from __future__ import annotations

"""Shared YAML sanitization helpers for Architect/PO outputs."""

import re
from typing import Any

import yaml


def sanitize_yaml_block(value: Any) -> str:
    """Return a clean YAML string from a value or existing YAML text."""
    if not value:
        return ""
    if isinstance(value, str):
        cleaned = re.sub(r"```(?:yaml)?", "", value, flags=re.IGNORECASE)
        cleaned = cleaned.replace("```", "")
        return cleaned.strip()
    try:
        return yaml.safe_dump(
            value,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        ).strip()
    except yaml.YAMLError:
        return str(value).strip()


def sanitize_po_yaml(content: str) -> str:
    """Product Owner-specific normalization with backtick cleanup."""
    if not content.strip():
        return content
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError:
        cleaned = re.sub(r'`([^`]+?)`', r"\1", content)
        try:
            data = yaml.safe_load(cleaned)
        except yaml.YAMLError:
            return content.strip()
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).strip()


def sanitize_requirements_yaml(content: str) -> str:
    """Normalize requirements.yaml content emitted with markdown fences/bold."""
    if not content:
        return ""
    cleaned = sanitize_yaml_block(content)
    # Strip bold markers that break YAML (`**text**`)
    cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", cleaned)
    return cleaned


def normalize_po_yaml(content: str) -> str:
    """Pre-process LLM output (Gemini quirks) for PO."""
    _THIN_SPACE_CHARS = ("\u202f", "\u00a0", "\u2007")
    lines = content.splitlines()
    normalized: list[str] = []
    for raw_line in lines:
        line = raw_line
        for ch in _THIN_SPACE_CHARS:
            if ch in line:
                line = line.replace(ch, " ")

        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if stripped.startswith("-"):
            payload = stripped[1:].lstrip()
            if payload:
                needs_quote = False
                if payload[0] in ("%", "&", "*", "#", "!", "?", "@", "[", "]", "{", "}", ","):
                    needs_quote = True
                elif payload[0] in (">", "<"):
                    needs_quote = True
                else:
                    colon_idx = payload.find(":")
                    if colon_idx != -1:
                        key_part = payload[:colon_idx]
                        remainder = payload[colon_idx + 1 :].strip()
                        key_has_spaces = " " in key_part.strip()
                        key_has_unicode = any(ord(ch) > 127 for ch in key_part)
                        key_is_simple = re.fullmatch(r"[\w-]+", key_part.strip() or "") is not None
                        if remainder and (key_has_spaces or key_has_unicode) and not key_is_simple:
                            needs_quote = True

                first_token = payload.split()[0] if payload.split() else ""
                if "%" in first_token:
                    needs_quote = True

                if needs_quote:
                    payload_q = payload.replace('"', '\\"')
                    line = " " * indent + f"- \"{payload_q}\""
        else:
            if stripped and stripped[0] in (">", "<"):
                payload = stripped.replace('"', '\\"')
                line = " " * indent + f"\"{payload}\""

        normalized.append(line)

    return "\n".join(normalized)
