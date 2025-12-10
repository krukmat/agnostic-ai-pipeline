"""Analytics utilities for Chain-of-Thought (CoT) logs.

Consumes the JSONL stream produced by `cot_tracker.py` and generates
summaries that highlight how many thoughts occurred per phase/layer,
the distribution of decision kinds, low-confidence actions, and
escalation hotspots. The module intentionally keeps the aggregation
logic pure so it can be tested directly without touching the file
system, while the CLI simply wires file IO.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from logger import logger

DEFAULT_INPUT = Path("artifacts/cot_layer6/thoughts.jsonl")
DEFAULT_OUTPUT_DIR = Path("artifacts/cot_layer6")


@dataclass
class AggregatedAnalytics:
    """Structured analytics derived from CoT logs."""

    total_entries: int
    phases: Dict[str, int]
    layers: Dict[str, int]
    kinds: Dict[str, int]
    average_confidence: float
    low_confidence_entries: List[Dict[str, Any]]
    escalations: Dict[str, Any]
    recent_messages: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serializable representation."""
        return {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "total_entries": self.total_entries,
            "phases": dict(self.phases),
            "layers": dict(self.layers),
            "kinds": dict(self.kinds),
            "average_confidence": self.average_confidence,
            "low_confidence_entries": self.low_confidence_entries,
            "escalations": self.escalations,
            "recent_messages": self.recent_messages,
        }


def load_thoughts(path: Path) -> List[Dict[str, Any]]:
    """Load JSONL CoT entries from disk.

    Returns an empty list if the file does not exist or is unreadable.
    """
    if not path.exists():
        logger.debug(f"[cot-analytics] Input file missing: {path}")
        return []

    thoughts: List[Dict[str, Any]] = []
    with path.open("r") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                thoughts.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                logger.warning(
                    "[cot-analytics] Skipping invalid JSONL entry: %s (%s)",
                    stripped[:120],
                    exc,
                )
    logger.debug(f"[cot-analytics] Loaded {len(thoughts)} entries from {path}")
    return thoughts


def aggregate_thoughts(
    thoughts: Iterable[Dict[str, Any]],
    low_conf_threshold: float = 0.75,
) -> AggregatedAnalytics:
    """Compute aggregate stats from CoT entries."""
    phase_counts: Counter[str] = Counter()
    layer_counts: Counter[str] = Counter()
    kind_counts: Counter[str] = Counter()
    total_conf = 0.0
    counted_conf = 0
    low_conf: List[Dict[str, Any]] = []
    escalations_total = 0
    escalations_by_story: Counter[str] = Counter()
    recent_messages: List[str] = []

    for entry in thoughts:
        phase = entry.get("phase", "UNKNOWN")
        layer = entry.get("layer", "unknown")
        kind = entry.get("kind", "unknown")
        confidence = entry.get("confidence")
        message = entry.get("message", "")

        phase_counts[phase] += 1
        layer_counts[layer] += 1
        kind_counts[kind] += 1

        if isinstance(confidence, (int, float)):
            total_conf += confidence
            counted_conf += 1
            if confidence < low_conf_threshold:
                low_conf.append({
                    "timestamp": entry.get("timestamp"),
                    "phase": phase,
                    "layer": layer,
                    "kind": kind,
                    "confidence": confidence,
                    "message": message,
                })

        if kind == "escalation":
            escalations_total += 1
            story_id = _extract_story_id(entry)
            if story_id:
                escalations_by_story[story_id] += 1

        if message:
            recent_messages.append(message)

    total_entries = sum(phase_counts.values())
    average_confidence = (
        total_conf / counted_conf if counted_conf > 0 else 0.0
    )

    escalations = {
        "total": escalations_total,
        "by_story": dict(escalations_by_story),
    }

    # Keep most recent 10 messages for readability
    recent_messages = recent_messages[-10:]

    return AggregatedAnalytics(
        total_entries=total_entries,
        phases=dict(phase_counts),
        layers=dict(layer_counts),
        kinds=dict(kind_counts),
        average_confidence=round(average_confidence, 4),
        low_confidence_entries=low_conf,
        escalations=escalations,
        recent_messages=recent_messages,
    )


def _extract_story_id(entry: Dict[str, Any]) -> Optional[str]:
    """Helper that extracts story id from entry details/inputs."""
    details = entry.get("details") or {}
    inputs = entry.get("inputs") or {}
    story_id = (
        details.get("story_id")
        or details.get("story")
        or inputs.get("story_id")
    )
    if story_id and isinstance(story_id, str):
        return story_id
    return None


def write_json_report(summary: AggregatedAnalytics, path: Path) -> None:
    """Persist analytics summary to JSON."""
    with path.open("w") as handle:
        json.dump(summary.to_dict(), handle, indent=2)


def write_markdown_report(summary: AggregatedAnalytics, path: Path) -> None:
    """Persist analytics summary to Markdown."""
    lines = [
        "# Chain of Thought Analytics Summary\n",
        f"- Generated: {datetime.utcnow().isoformat()}Z",
        f"- Entries analyzed: {summary.total_entries}",
        f"- Average confidence: {summary.average_confidence:.2f}",
        "",
        "## Thought Distribution",
        "",
        "### By Phase",
    ]

    if summary.phases:
        for phase, count in sorted(summary.phases.items()):
            lines.append(f"- {phase}: {count}")
    else:
        lines.append("- No phase data")

    lines.extend([
        "",
        "### By Layer",
    ])
    if summary.layers:
        for layer, count in sorted(summary.layers.items()):
            lines.append(f"- {layer}: {count}")
    else:
        lines.append("- No layer data")

    lines.extend([
        "",
        "### By Kind",
    ])
    if summary.kinds:
        for kind, count in sorted(summary.kinds.items()):
            lines.append(f"- {kind}: {count}")
    else:
        lines.append("- No kind data")

    lines.extend([
        "",
        "## Escalations",
        f"- Total escalations: {summary.escalations.get('total', 0)}",
    ])
    by_story = summary.escalations.get("by_story") or {}
    if by_story:
        lines.append("- By story:")
        for story_id, count in sorted(by_story.items()):
            lines.append(f"  - {story_id}: {count}")
    else:
        lines.append("- No per-story escalation data.")

    lines.extend([
        "",
        "## Low Confidence Entries",
    ])
    if summary.low_confidence_entries:
        for entry in summary.low_confidence_entries[:10]:
            lines.append(
                f"- {entry['timestamp']} [{entry['phase']}/{entry['layer']}] "
                f"{entry['kind']} → {entry['confidence']:.2f}: {entry['message']}"
            )
    else:
        lines.append("- None detected below threshold.")

    lines.extend([
        "",
        "## Recent Messages",
    ])
    if summary.recent_messages:
        for message in summary.recent_messages:
            lines.append(f"- {message}")
    else:
        lines.append("- No messages recorded.")

    with path.open("w") as handle:
        handle.write("\n".join(lines) + "\n")


def generate_reports(
    input_path: Path,
    output_dir: Path,
    low_conf_threshold: float = 0.75,
) -> AggregatedAnalytics:
    """End-to-end helper used by CLI/tests."""
    thoughts = load_thoughts(input_path)
    summary = aggregate_thoughts(thoughts, low_conf_threshold=low_conf_threshold)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json_report(summary, output_dir / "analytics.json")
    write_markdown_report(summary, output_dir / "analytics.md")
    logger.info(
        "[cot-analytics] Wrote analytics to %s (entries=%s)",
        output_dir,
        summary.total_entries,
    )
    return summary


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CoT analytics generator")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to CoT JSONL file (default: artifacts/cot_layer6/thoughts.jsonl)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Where to write analytics.json and analytics.md",
    )
    parser.add_argument(
        "--low-confidence-threshold",
        type=float,
        default=0.75,
        help="Confidence threshold for flagging entries",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = _parse_args(argv)
    generate_reports(
        input_path=args.input,
        output_dir=args.output_dir,
        low_conf_threshold=args.low_confidence_threshold,
    )


if __name__ == "__main__":
    main()
