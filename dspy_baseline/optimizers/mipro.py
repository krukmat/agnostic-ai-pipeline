"""Wrapper around dspy.MIPROv2 to compile DSPy programs."""

from __future__ import annotations

from typing import Any, Callable, Iterable, Optional

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
    valset: Optional[Iterable[Any]] = None,
    stop_metric: Optional[Callable[[Any, Any], float]] = None,
    **compile_kwargs: Any,
) -> Any:
    """Compile and return an optimized DSPy program using MIPROv2.

    Parameters
    ----------
    program:
        DSPy module to compile (e.g., BARequirementsModule, QA ChainOfThought program).
    trainset:
        Iterable of `dspy.Example` instances used for optimization.
    metric:
        Callable that returns a score in [0, 1] given `(example, prediction)`.
    num_candidates / num_trials / max_bootstrapped_demos / seed:
        Parameters passed to `dspy.MIPROv2`.
    valset:
        Optional iterable of validation examples.
    stop_metric:
        Optional callable evaluated on the validation set to trigger early stop.
    compile_kwargs:
        Additional keyword arguments forwarded to `teleprompter.compile(...)`.

    Returns
    -------
    Compiled DSPy program ready for inference.
    """
    teleprompter = dspy.MIPROv2(
        metric=metric,
        auto=None,  # Required to use manual num_candidates/num_trials settings
        num_candidates=num_candidates,
        seed=seed,
    )

    compile_args = {
        "trainset": trainset,
        "num_trials": num_trials,
        "max_bootstrapped_demos": max_bootstrapped_demos,
        "minibatch_size": 10,  # Set to avoid exceeding valset size
    }
    if valset is not None:
        compile_args["valset"] = valset
    # stop_metric not supported by current DSPy release for MIPROv2.compile
    compile_args.update(compile_kwargs)

    compiled_program = teleprompter.compile(program, **compile_args)
    return compiled_program
