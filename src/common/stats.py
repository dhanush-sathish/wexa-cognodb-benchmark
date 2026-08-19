import json
import time
from contextlib import contextmanager

import numpy as np


class Timer:
    """Collects wall-clock durations (ms) for repeated operations."""

    def __init__(self):
        self.samples_ms = []

    @contextmanager
    def measure(self):
        start = time.perf_counter()
        try:
            yield
        finally:
            self.samples_ms.append((time.perf_counter() - start) * 1000.0)

    def percentiles(self):
        if not self.samples_ms:
            return {"p50_ms": None, "p95_ms": None, "p99_ms": None, "mean_ms": None, "n": 0}
        arr = np.array(self.samples_ms)
        return {
            "p50_ms": round(float(np.percentile(arr, 50)), 3),
            "p95_ms": round(float(np.percentile(arr, 95)), 3),
            "p99_ms": round(float(np.percentile(arr, 99)), 3),
            "mean_ms": round(float(np.mean(arr)), 3),
            "n": len(arr),
        }


def write_result(results_dir, platform: str, payload: dict):
    results_dir.mkdir(parents=True, exist_ok=True)
    path = results_dir / f"{platform}.json"
    existing = {}
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
    existing.setdefault("platform", platform)
    existing.update(payload)
    path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    return path
