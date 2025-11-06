"""Wrapper around dspy.MIPROv2 to compile DSPy programs."""

from __future__ import annotations

from typing import Any, Callable, Iterable

import dspy


def optimize_program(
    program: Any,
    trainset: Iterable[Any],
    metric: Callable[[Any, Any], float],
    *,
    num_candidates: int = 8,
    num_trials: int = 8,
    max_bootstrapped_demos: int = 8,
    seed: int = 0,
) -> Any:
    """Compile and return an optimized DSPy program using MIPROv2.

    This helper is designed for CLI scripts that fine-tune Business Analyst
    or QA signatures with curated datasets. The caller is responsible for
    providing a trainset iterable and a metric callable that returns a score
    between 0.0 and 1.0 for each (example, prediction) pair.
    """
    optimizer = dspy.MIPROv2(
        metric=metric,
        auto=None,
        num_candidates=num_candidates,
        seed=seed,
    )
    compiled_program = optimizer.compile(
        program,
        trainset=trainset,
        num_trials=num_trials,
        max_bootstrapped_demos=max_bootstrapped_demos,
        minibatch_size=10,
    )
    return compiled_program

