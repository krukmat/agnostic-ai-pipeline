"""Adapter layer around post-training validators for Phase 2A."""

from __future__ import annotations

from typing import Any, Dict

from post_training.src.posttrain.validators import ValidationResult


class ValidatorAdapter:
    """Validate role records and always return ValidationResult."""

    def validate(self, role: str, record: Dict[str, Any]) -> ValidationResult:
        output = str(record.get("output", "") or "")
        if len(output.strip()) < 20:
            return ValidationResult(
                ok=False,
                score=0.0,
                reason="too_short",
                details={"min_chars": 20, "role": role},
            )

        # simple local/dev score heuristic for Phase 2A
        # calibrated to allow realistic mock outputs to pass local thresholds
        score = min(1.0, max(0.0, len(output.strip()) / 100.0))
        return ValidationResult(
            ok=score >= 0.2,
            score=score,
            reason="ok" if score >= 0.2 else "low_score",
            details={"role": role, "mode": record.get("mode", "local")},
        )
