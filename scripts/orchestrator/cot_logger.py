"""
Chain-of-Thought Logger for structured reasoning capture.

Logs all orchestrator decisions with their reasoning, alternatives, and confidence.
Exports chains as JSON for later analysis and learning.
"""

from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
import json
from logger import logger


class ChainOfThoughtLogger:
    """Logs structured reasoning for orchestrator decisions."""

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize CoT logger with output directory.

        Args:
            output_dir: Directory to save chain files. Defaults to artifacts/cot
        """
        self.output_dir = output_dir or Path("artifacts/cot")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_chain: Dict = {}
        self.all_chains: List[Dict] = []
        logger.info(f"[cot_logger] Initialized, output_dir={self.output_dir}")

    def start_chain(self, step: int, phase: str) -> None:
        """Start a new chain of thought for a pipeline step.

        Args:
            step: Step number in pipeline
            phase: Pipeline phase name
        """
        self.current_chain = {
            "step": step,
            "phase": phase,
            "timestamp": datetime.now().isoformat(),
            "reasoning": [],
        }
        logger.debug(f"[cot_logger] Started chain for step {step}, phase {phase}")

    def log_decision(
        self,
        decision: str,
        rule: str,
        confidence: float,
        alternatives: Optional[List[str]] = None,
    ) -> None:
        """Log a decision point in the chain.

        Args:
            decision: Description of the decision made
            rule: Rule/policy used to make decision
            confidence: Confidence level (0.0-1.0)
            alternatives: Other options considered
        """
        if not self.current_chain:
            logger.warning("[cot_logger] No active chain, call start_chain() first")
            return

        self.current_chain["reasoning"].append({
            "type": "decision",
            "decision": decision,
            "rule": rule,
            "confidence": confidence,
            "alternatives": alternatives or [],
            "timestamp": datetime.now().isoformat(),
        })

    def log_evaluation(
        self, condition: str, result: bool, reason: str
    ) -> None:
        """Log condition evaluation in the chain.

        Args:
            condition: Condition being evaluated
            result: Result of evaluation
            reason: Explanation for result
        """
        if not self.current_chain:
            logger.warning("[cot_logger] No active chain, call start_chain() first")
            return

        self.current_chain["reasoning"].append({
            "type": "evaluation",
            "condition": condition,
            "result": result,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        })

    def end_chain(self) -> Dict:
        """End current chain and save to file.

        Returns:
            The completed chain dict
        """
        if not self.current_chain:
            logger.warning("[cot_logger] No active chain to end")
            return {}

        chain = self.current_chain
        self.all_chains.append(chain)
        self._save_chain(chain)
        self.current_chain = {}

        logger.debug(
            f"[cot_logger] Ended chain: step={chain['step']}, "
            f"reasoning_items={len(chain['reasoning'])}"
        )

        return chain

    def _save_chain(self, chain: Dict) -> None:
        """Save individual chain to JSON file.

        Args:
            chain: Chain dict to save
        """
        try:
            step = chain.get("step", 0)
            path = self.output_dir / f"step_{step:03d}.json"
            path.write_text(json.dumps(chain, indent=2))
            logger.debug(f"[cot_logger] Saved chain to {path}")
        except Exception as e:
            logger.error(f"[cot_logger] Failed to save chain: {e}")

    def export_summary(self) -> Dict:
        """Export summary of all chains collected.

        Returns:
            Dict with total_steps, chains list, and decision_tree
        """
        summary = {
            "total_steps": len(self.all_chains),
            "chains": self.all_chains,
            "decision_tree": self._build_tree(),
        }

        # Save summary to file
        try:
            summary_path = self.output_dir / "summary.json"
            summary_path.write_text(json.dumps(summary, indent=2))
            logger.debug(f"[cot_logger] Exported summary to {summary_path}")
        except Exception as e:
            logger.error(f"[cot_logger] Failed to export summary: {e}")

        return summary

    def _build_tree(self) -> Dict:
        """Build decision tree structure from all chains.

        Returns:
            Dict mapping phases to their decision counts per step
        """
        tree = {}
        for chain in self.all_chains:
            phase = chain.get("phase", "unknown")
            step = chain.get("step", 0)

            if phase not in tree:
                tree[phase] = []

            tree[phase].append({
                "step": step,
                "reasoning_count": len(chain.get("reasoning", [])),
                "timestamp": chain.get("timestamp"),
            })

        return tree

    def get_chain_count(self) -> int:
        """Get total number of chains recorded.

        Returns:
            Count of chains
        """
        return len(self.all_chains)

    def get_reasoning_count(self) -> int:
        """Get total reasoning items across all chains.

        Returns:
            Total count of reasoning entries
        """
        return sum(
            len(chain.get("reasoning", [])) for chain in self.all_chains
        )
