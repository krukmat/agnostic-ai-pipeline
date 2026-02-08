"""Quality filtering step for synthetic records."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .validators_adapter import ValidatorAdapter


class QualityFilterStep:
    """Evaluate records and mark pass/fail for regeneration."""

    def __init__(self, role: str, min_score: float = 0.85):
        self.role = role
        self.min_score = min_score
        self.validator_adapter = ValidatorAdapter()
        self.stats = {"passed": 0, "failed": 0, "filtered": 0}

    def _score_output(self, input_data: Dict[str, Any]) -> Tuple[float, str]:
        result = self.validator_adapter.validate(self.role, input_data)
        feedback = result.reason if hasattr(result, "reason") else "ok"
        return result.score, feedback

    def process(self, inputs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        self.stats = {"passed": 0, "failed": 0, "filtered": 0}

        for input_data in inputs:
            score, feedback = self._score_output(input_data)
            passed = score >= self.min_score
            row = {
                **input_data,
                "quality_score": score,
                "quality_feedback": feedback,
                "passed": passed,
            }
            if not passed:
                row["retry"] = True
                self.stats["filtered"] += 1
            else:
                self.stats["passed"] += 1
            results.append(row)

        self.stats["failed"] = len(inputs) - self.stats["passed"]
        return results

    def get_stats(self) -> Dict[str, int]:
        return dict(self.stats)
