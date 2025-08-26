"""Measure EventBus overhead vs direct call baseline.

 Simplistic micro-benchmark: executes N synthetic GenerationCompleted emits
 (through core.events.emit) versus a no-op loop to approximate relative
 overhead.
Outputs JSON with total_ms and per_event_us plus overhead_ratio.

Not a rigorous perf test; intended to document <2% target qualitatively.
"""
from __future__ import annotations

import json
import time
from statistics import mean
import sys
import os

# ensure repository root on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.events import emit, GenerationCompleted  # noqa: E402

N = 2000


def bench_events(n: int) -> float:  # ms
    start = time.time()
    for i in range(n):
        emit(
            GenerationCompleted(
                request_id=f"r{i}",
                model_id="bench",
                role="primary",
                status="ok",
                correlation_id=f"r{i}",
                output_tokens=10,
                latency_ms=5,
                result_summary=None,
            )
        )
    return (time.time() - start) * 1000


def bench_baseline(n: int) -> float:  # ms
    start = time.time()
    # minimal work approximating loop overhead
    for _ in range(n):
        pass
    return (time.time() - start) * 1000


def main():  # noqa: D401
    runs = 5
    event_ms = []
    base_ms = []
    for _ in range(runs):
        event_ms.append(bench_events(N))
        base_ms.append(bench_baseline(N))
    ev_avg = mean(event_ms)
    base_avg = mean(base_ms)
    per_event_us = (ev_avg / N) * 1000
    overhead_ratio = (ev_avg - base_avg) / ev_avg if ev_avg else 0.0
    print(
        json.dumps(
            {
                "iterations": N,
                "event_avg_ms": round(ev_avg, 3),
                "baseline_avg_ms": round(base_avg, 3),
                "per_event_us": round(per_event_us, 3),
                "overhead_ratio": round(overhead_ratio, 4),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":  # pragma: no cover
    main()
