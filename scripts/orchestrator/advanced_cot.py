"""
Advanced Chain-of-Thought Logging with hierarchical reasoning.

Extends Phase 2 CoT with:
- Nested sub-chains within phases
- Alternative option analysis with scoring
- Constraint evaluation logging
- Natural language reasoning summaries
"""

from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
import json
from logger import logger


class AdvancedChainOfThought:
    """Advanced CoT logging with hierarchical reasoning and alternatives."""

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize advanced CoT logger.

        Args:
            output_dir: Directory for chain storage. Defaults to artifacts/cot_advanced
        """
        self.output_dir = output_dir or Path("artifacts/cot_advanced")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_chain: Dict = {}
        self.sub_chains: Dict[str, Dict] = {}
        self.all_chains: List[Dict] = []
        logger.info(f"[cot_advanced] Initialized: {self.output_dir}")

    def start_chain(self, step: int, phase: str) -> None:
        """Start a new main chain.

        Args:
            step: Step number
            phase: Pipeline phase
        """
        self.current_chain = {
            "step": step,
            "phase": phase,
            "timestamp": datetime.now().isoformat(),
            "reasoning": [],
            "sub_chains": {},
            "constraints": [],
        }
        self.sub_chains = {}
        logger.debug(f"[cot_advanced] Started chain: step={step}, phase={phase}")

    def start_sub_chain(self, name: str) -> str:
        """Start a nested sub-chain within current chain.

        Args:
            name: Sub-chain name (e.g., "ready_check", "escalation_check")

        Returns:
            Sub-chain ID for reference
        """
        chain_id = f"{self.current_chain['step']}_{name}"
        self.sub_chains[chain_id] = {
            "id": chain_id,
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "decisions": [],
            "evaluations": [],
        }
        logger.debug(f"[cot_advanced] Started sub-chain: {chain_id}")
        return chain_id

    def log_alternative_analysis(
        self,
        alternatives: Dict[str, Dict],
        chosen: str,
        rule: str = "best_score",
    ) -> None:
        """Log analysis of multiple alternatives with scoring.

        Args:
            alternatives: {option_name: {score, reason, metrics: {...}}}
            chosen: Name of chosen alternative
            rule: Rule used to select alternative
        """
        entry = {
            "type": "alternative_analysis",
            "alternatives": alternatives,
            "chosen": chosen,
            "rule": rule,
            "timestamp": datetime.now().isoformat(),
        }

        self.current_chain["reasoning"].append(entry)

        logger.debug(
            f"[cot_advanced] Alternative analysis: "
            f"{len(alternatives)} options, chose {chosen} "
            f"(score={alternatives[chosen]['score']})"
        )

    def log_constraint_check(
        self,
        constraint_name: str,
        satisfied: bool,
        reason: str,
        details: Optional[Dict] = None,
    ) -> None:
        """Log constraint evaluation.

        Args:
            constraint_name: Name of constraint (e.g., "max_retries", "parallelism")
            satisfied: Whether constraint is satisfied
            reason: Why constraint is/isn't satisfied
            details: Optional additional details
        """
        entry = {
            "constraint": constraint_name,
            "satisfied": satisfied,
            "reason": reason,
            "details": details or {},
            "timestamp": datetime.now().isoformat(),
        }

        self.current_chain["constraints"].append(entry)

        logger.debug(
            f"[cot_advanced] Constraint check: {constraint_name}={satisfied} "
            f"({reason})"
        )

    def log_decision(
        self,
        decision: str,
        rule: str,
        confidence: float,
        alternatives: Optional[List[str]] = None,
        sub_chain_id: Optional[str] = None,
    ) -> None:
        """Log a decision point.

        Args:
            decision: Description of decision
            rule: Rule/policy used
            confidence: Confidence level (0.0-1.0)
            alternatives: Options considered
            sub_chain_id: Optional sub-chain to log to
        """
        entry = {
            "type": "decision",
            "decision": decision,
            "rule": rule,
            "confidence": confidence,
            "alternatives": alternatives or [],
            "timestamp": datetime.now().isoformat(),
        }

        if sub_chain_id and sub_chain_id in self.sub_chains:
            self.sub_chains[sub_chain_id]["decisions"].append(entry)
        else:
            self.current_chain["reasoning"].append(entry)

        logger.debug(
            f"[cot_advanced] Decision: {decision} (confidence={confidence:.2f})"
        )

    def log_evaluation(
        self,
        condition: str,
        result: bool,
        reason: str,
        sub_chain_id: Optional[str] = None,
    ) -> None:
        """Log condition evaluation.

        Args:
            condition: Condition being evaluated
            result: Evaluation result
            reason: Why result is true/false
            sub_chain_id: Optional sub-chain to log to
        """
        entry = {
            "type": "evaluation",
            "condition": condition,
            "result": result,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }

        if sub_chain_id and sub_chain_id in self.sub_chains:
            self.sub_chains[sub_chain_id]["evaluations"].append(entry)
        else:
            self.current_chain["reasoning"].append(entry)

        logger.debug(
            f"[cot_advanced] Evaluation: {condition}={result} ({reason})"
        )

    def end_chain(self) -> Dict:
        """End current chain, generate summary, and save.

        Returns:
            Completed chain with summary
        """
        if not self.current_chain:
            logger.warning("[cot_advanced] No active chain to end")
            return {}

        # Add sub-chains to main chain
        self.current_chain["sub_chains"] = self.sub_chains

        # Generate summary
        summary = self._generate_reasoning_summary()
        self.current_chain["summary"] = summary

        # Save chain
        chain = self.current_chain
        self.all_chains.append(chain)
        self._save_chain(chain)

        self.current_chain = {}
        self.sub_chains = {}

        logger.debug(
            f"[cot_advanced] Ended chain: "
            f"{len(chain['reasoning'])} reasoning items, "
            f"{len(chain['sub_chains'])} sub-chains"
        )

        return chain

    def _generate_reasoning_summary(self) -> str:
        """Generate natural language summary of reasoning.

        Returns:
            Natural language reasoning summary
        """
        if not self.current_chain["reasoning"]:
            return "No reasoning recorded"

        parts = []

        # Summarize decisions
        decisions = [
            r for r in self.current_chain["reasoning"]
            if r.get("type") == "decision"
        ]
        if decisions:
            chosen = decisions[-1].get("decision", "unknown")
            reason = decisions[-1].get("rule", "based on rules")
            parts.append(f"Selected '{chosen}' {reason}")

        # Summarize constraints
        constraints = self.current_chain["constraints"]
        if constraints:
            satisfied = sum(1 for c in constraints if c.get("satisfied"))
            parts.append(
                f"Evaluated {len(constraints)} constraints "
                f"({satisfied} satisfied)"
            )

        # Summarize alternatives
        alternatives = [
            r for r in self.current_chain["reasoning"]
            if r.get("type") == "alternative_analysis"
        ]
        if alternatives:
            chosen = alternatives[-1].get("chosen")
            parts.append(f"Chose alternative: {chosen}")

        summary = "; ".join(parts)
        return summary

    def export_decision_tree(self, format: str = "json") -> Dict:
        """Export complete decision tree structure.

        Args:
            format: Output format (json or dict)

        Returns:
            Decision tree structure
        """
        tree = {
            "total_chains": len(self.all_chains),
            "total_decisions": sum(
                len(c.get("reasoning", []))
                for c in self.all_chains
            ),
            "phases": {},
        }

        # Group by phase
        for chain in self.all_chains:
            phase = chain.get("phase", "unknown")
            if phase not in tree["phases"]:
                tree["phases"][phase] = {
                    "chains": [],
                    "decision_count": 0,
                    "constraint_count": 0,
                }

            phase_info = {
                "step": chain.get("step"),
                "decisions": len(chain.get("reasoning", [])),
                "sub_chains": len(chain.get("sub_chains", {})),
                "constraints": len(chain.get("constraints", [])),
                "summary": chain.get("summary", ""),
            }

            tree["phases"][phase]["chains"].append(phase_info)
            tree["phases"][phase]["decision_count"] += phase_info["decisions"]
            tree["phases"][phase]["constraint_count"] += phase_info["constraints"]

        return tree

    def _save_chain(self, chain: Dict) -> None:
        """Save chain to file.

        Args:
            chain: Chain to save
        """
        try:
            step = chain.get("step", 0)
            path = self.output_dir / f"step_{step:03d}_advanced.json"
            path.write_text(json.dumps(chain, indent=2))
            logger.debug(f"[cot_advanced] Saved chain: {path}")
        except Exception as e:
            logger.warning(f"[cot_advanced] Failed to save chain: {e}")

    def export_summary(self) -> Dict:
        """Export comprehensive CoT summary.

        Returns:
            Dict with all chains and analysis
        """
        summary = {
            "total_chains": len(self.all_chains),
            "total_reasoning_items": sum(
                len(c.get("reasoning", []))
                for c in self.all_chains
            ),
            "chains": self.all_chains,
            "decision_tree": self.export_decision_tree(),
        }

        # Save summary
        try:
            summary_path = self.output_dir / "summary_advanced.json"
            summary_path.write_text(json.dumps(summary, indent=2))
            logger.debug(f"[cot_advanced] Exported summary to {summary_path}")
        except Exception as e:
            logger.warning(f"[cot_advanced] Failed to export summary: {e}")

        return summary

    def get_chain_statistics(self) -> Dict:
        """Get statistics about all chains.

        Returns:
            Dict with chain statistics
        """
        total_decisions = 0
        total_alternatives = 0
        total_constraints = 0

        for chain in self.all_chains:
            total_decisions += len(chain.get("reasoning", []))
            total_constraints += len(chain.get("constraints", []))

            for item in chain.get("reasoning", []):
                if item.get("type") == "alternative_analysis":
                    total_alternatives += 1

        return {
            "total_chains": len(self.all_chains),
            "total_decisions": total_decisions,
            "total_alternatives": total_alternatives,
            "total_constraints": total_constraints,
            "avg_decisions_per_chain": (
                total_decisions / len(self.all_chains)
                if self.all_chains else 0
            ),
        }
