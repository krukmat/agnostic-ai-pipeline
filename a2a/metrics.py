from __future__ import annotations

import time
import json
from functools import wraps
from typing import Any, Dict, List
from pathlib import Path
import datetime

ROOT = Path(__file__).resolve().parents[1]
METRICS_DIR = ROOT / "artifacts" / "metrics"
METRICS_DIR.mkdir(parents=True, exist_ok=True)

_metrics: List[Dict[str, Any]] = []


def record_metric(metric: Dict[str, Any]):
    """Record a single metric entry."""
    _metrics.append(metric)


def save_metrics():
    """Save all recorded metrics to a timestamped JSON file."""
    if not _metrics:
        return

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_path = METRICS_DIR / f"{timestamp}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(_metrics, f, indent=2)
    _metrics.clear()


def instrumented(role: str):
    """Decorator to instrument a role's execution time."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.perf_counter() - start_time
                record_metric({
                    "role": role,
                    "duration_seconds": round(duration, 3),
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                })
        return wrapper
    return decorator
