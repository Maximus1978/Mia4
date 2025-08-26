"""Minimal in-memory metrics collector.

Purpose:
  - Counters and simple latency samples for early degradation detection.
  - Zero external deps; can be swapped by Prometheus exporter later.

API (intentionally tiny):
  inc(name, labels=None, value=1)
  observe(name, value, labels=None)
  snapshot() -> dict (copy for safe reading)

Thread-safety: coarse RLock; overhead negligible for low event volume.
"""
from __future__ import annotations

from threading import RLock
from time import time
from typing import Dict, Tuple, Any

_COUNTERS: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], float] = {}
_HIST: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], list] = {}
_LOCK = RLock()


def _norm_labels(labels: dict[str, Any] | None) -> Tuple[Tuple[str, str], ...]:
    if not labels:
        return tuple()
    return tuple(sorted((str(k), str(v)) for k, v in labels.items()))


def inc(
    name: str,
    labels: dict[str, Any] | None = None,
    value: float = 1.0,
) -> None:
    key = (name, _norm_labels(labels))
    with _LOCK:
        _COUNTERS[key] = _COUNTERS.get(key, 0.0) + value


def observe(
    name: str,
    value: float,
    labels: dict[str, Any] | None = None,
) -> None:
    key = (name, _norm_labels(labels))
    with _LOCK:
        _HIST.setdefault(key, []).append(value)


def snapshot() -> dict[str, Any]:
    with _LOCK:
        counters = {}
        for (name, labels), v in _COUNTERS.items():
            label_str = ""
            if labels:
                label_str = "{" + ",".join(f"{k}={v}" for k, v in labels) + "}"
            counters[name + label_str] = v
        hist = {}
        for (name, labels), vals in _HIST.items():
            if not vals:
                continue
            label_str = ""
            if labels:
                label_str = "{" + ",".join(f"{k}={v}" for k, v in labels) + "}"
            hist[name + label_str] = {
                "count": len(vals),
                "min": min(vals),
                "max": max(vals),
                "p50": sorted(vals)[len(vals) // 2],
                "last": vals[-1],
            }
        return {
            "ts": time(),
            "counters": counters,
            "histograms": hist,
        }


def reset_for_tests() -> None:  # pragma: no cover
    with _LOCK:
        _COUNTERS.clear()
        _HIST.clear()


__all__ = [
    "inc",
    "observe",
    "snapshot",
    "reset_for_tests",
]
