"""Layer 6: Chain of Thought Tracker

Unified thought tracking across all orchestration layers:
- State Machine transitions
- DAG decisions
- Policy evaluations
- Planner decisions
- LLM decisions
- Escalations

Exports to JSONL (machine) and Markdown (human) formats.
"""
from dataclasses import dataclass, asdict, field
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
import json


@dataclass
class ThoughtEntry:
    """Single thought/decision in the orchestration chain."""
    timestamp: str                  # ISO 8601 format
    phase: str                      # Pipeline phase
    layer: str                      # Origin layer (state_machine, dag, policy, planner, llm)
    kind: str                       # Entry type (transition, decision, policy_eval, escalation, llm_call)
    message: str                    # Human summary
    details: Dict[str, Any]         # Full context
    inputs: Dict[str, Any]          # Input values
    reasoning_steps: List[str]      # Reasoning trace
    output: Any                     # Result
    confidence: float               # 1.0 = deterministic, <1.0 = LLM


class ChainOfThoughtTracker:
    """Unified tracker for all orchestration layers' decisions and reasoning."""

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize tracker with output directory."""
        if output_dir is None:
            output_dir = Path("artifacts/cot_layer6")

        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.thoughts: List[ThoughtEntry] = []
        self.phase = "DEVELOPMENT"  # Default phase, updated externally

    def log_state_transition(self, from_phase: str, to_phase: str, reason: str) -> None:
        """Log state machine phase transition."""
        entry = ThoughtEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            phase=to_phase,
            layer="state_machine",
            kind="transition",
            message=f"State transition: {from_phase} → {to_phase}",
            details={
                "from_phase": from_phase,
                "to_phase": to_phase,
                "reason": reason
            },
            inputs={"from": from_phase, "to": to_phase},
            reasoning_steps=["validate_transition", "update_state"],
            output=to_phase,
            confidence=1.0
        )
        self.thoughts.append(entry)

    def log_dag_decision(self, ready_stories: List[str], batch: List[str], reason: str) -> None:
        """Log DAG batch selection decision."""
        entry = ThoughtEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            phase=self.phase,
            layer="dag",
            kind="decision",
            message=f"DAG decision: selected {len(batch)} from {len(ready_stories)} ready stories",
            details={
                "total_ready": len(ready_stories),
                "batch_size": len(batch),
                "reason": reason
            },
            inputs={"ready_stories": ready_stories},
            reasoning_steps=["analyze_dependencies", "respect_constraints", "select_batch"],
            output=batch,
            confidence=1.0
        )
        self.thoughts.append(entry)

    def log_policy_evaluation(self, policy_name: str, condition: str, matched: bool,
                             context: Dict[str, Any]) -> None:
        """Log policy engine evaluation."""
        entry = ThoughtEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            phase=self.phase,
            layer="policy",
            kind="policy_eval",
            message=f"Policy '{policy_name}': {condition} = {matched}",
            details={
                "policy": policy_name,
                "condition": condition,
                "context": context
            },
            inputs={"policy": policy_name},
            reasoning_steps=["evaluate_condition", "check_context"],
            output=matched,
            confidence=1.0
        )
        self.thoughts.append(entry)

    def log_llm_decision(self, prompt: str, response: str, parsed: Dict[str, Any]) -> None:
        """Log LLM call and response."""
        entry = ThoughtEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            phase=self.phase,
            layer="llm",
            kind="llm_call",
            message=f"LLM decision: {parsed.get('action', 'unknown')}",
            details={
                "prompt_length": len(prompt),
                "model": "unknown",
                "response_preview": response[:100] if response else ""
            },
            inputs={"prompt": prompt},
            reasoning_steps=["call_llm", "parse_response"],
            output=parsed,
            confidence=parsed.get("confidence", 0.5)  # LLM confidence from response
        )
        self.thoughts.append(entry)

    def log_escalation_decision(self, story_id: str, action: str, reason: str) -> None:
        """Log escalation decision."""
        entry = ThoughtEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            phase=self.phase,
            layer="planner",
            kind="escalation",
            message=f"Escalation for {story_id}: {action}",
            details={
                "story_id": story_id,
                "reason": reason
            },
            inputs={"story_id": story_id},
            reasoning_steps=["detect_failure", "determine_escalation", "log_action"],
            output=action,
            confidence=1.0
        )
        self.thoughts.append(entry)

    def log_planner_decision(self, decision_type: str, alternatives: List[str],
                            chosen: str, confidence: float) -> None:
        """Log planner decision with alternatives."""
        entry = ThoughtEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            phase=self.phase,
            layer="planner",
            kind="decision",
            message=f"Planner decision: {decision_type} → {chosen}",
            details={
                "decision_type": decision_type,
                "num_alternatives": len(alternatives)
            },
            inputs={"alternatives": alternatives},
            reasoning_steps=["evaluate_options", "score_alternatives", "select_best"],
            output=chosen,
            confidence=confidence
        )
        self.thoughts.append(entry)

    def export_jsonl(self, path: Path) -> None:
        """Export all thoughts to JSONL format (one entry per line)."""
        with open(path, "w") as f:
            for thought in self.thoughts:
                # Convert dataclass to dict, handling non-JSON types
                thought_dict = asdict(thought)
                # Convert any non-serializable types to strings
                thought_dict = self._make_serializable(thought_dict)
                f.write(json.dumps(thought_dict) + "\n")

    def export_markdown(self, path: Path) -> None:
        """Export all thoughts to human-readable Markdown format."""
        lines = ["# Chain of Thought Report\n"]

        # Group by phase
        by_phase = self.get_thoughts_by_phase()

        for phase in sorted(by_phase.keys()):
            lines.append(f"\n## {phase} Phase\n")

            # Group by layer within phase
            thoughts_by_layer = {}
            for thought in by_phase[phase]:
                if thought.layer not in thoughts_by_layer:
                    thoughts_by_layer[thought.layer] = []
                thoughts_by_layer[thought.layer].append(thought)

            for layer in sorted(thoughts_by_layer.keys()):
                lines.append(f"\n### {layer.replace('_', ' ').title()} Layer\n")

                for i, thought in enumerate(thoughts_by_layer[layer], 1):
                    lines.append(f"**{i}. {thought.kind.upper()}**\n")
                    lines.append(f"- Time: {thought.timestamp}\n")
                    lines.append(f"- Message: {thought.message}\n")
                    lines.append(f"- Confidence: {thought.confidence:.2f}\n")

                    if thought.reasoning_steps:
                        lines.append(f"- Steps: {' → '.join(thought.reasoning_steps)}\n")

                    if thought.output:
                        output_str = str(thought.output)[:100]
                        lines.append(f"- Result: {output_str}\n")

                    lines.append("\n")

        Path(path).write_text("".join(lines))

    def get_thought_count(self) -> int:
        """Get total number of thoughts logged."""
        return len(self.thoughts)

    def get_thoughts_by_layer(self) -> Dict[str, int]:
        """Get thought count grouped by origin layer."""
        by_layer = {}
        for thought in self.thoughts:
            by_layer[thought.layer] = by_layer.get(thought.layer, 0) + 1
        return by_layer

    def get_thoughts_by_phase(self) -> Dict[str, List[ThoughtEntry]]:
        """Get all thoughts grouped by pipeline phase."""
        by_phase = {}
        for thought in self.thoughts:
            if thought.phase not in by_phase:
                by_phase[thought.phase] = []
            by_phase[thought.phase].append(thought)
        return by_phase

    def _make_serializable(self, obj: Any) -> Any:
        """Convert non-serializable objects to JSON-compatible types."""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, Path):
            return str(obj)
        elif not isinstance(obj, (str, int, float, bool, type(None))):
            return str(obj)
        return obj
