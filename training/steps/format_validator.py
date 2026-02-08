"""Format validation step for synthetic outputs."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


class FormatValidatorStep:
    """Validate minimal output contract for each generated record."""

    REQUIRED_FIELDS = ["instruction", "input", "output", "role", "metadata"]

    def __init__(self, role: str):
        self.role = role
        self.validation_errors: List[Dict[str, Any]] = []

    def _validate_row(self, row: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        for field in self.REQUIRED_FIELDS:
            if field not in row:
                errors.append(f"missing:{field}")
        if "metadata" in row and not isinstance(row["metadata"], dict):
            errors.append("metadata:not_object")
        return len(errors) == 0, errors

    def process(self, inputs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        self.validation_errors = []
        for row in inputs:
            ok, errors = self._validate_row(row)
            item = {**row, "format_valid": ok, "format_errors": errors or None}
            if not ok:
                item["retry"] = True
                self.validation_errors.append({"errors": errors, "row": row})
            out.append(item)
        return out

    def get_stats(self) -> Dict[str, Any]:
        return {
            "errors_count": len(self.validation_errors),
            "errors": self.validation_errors,
        }
