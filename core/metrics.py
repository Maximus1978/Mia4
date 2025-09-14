"""Minimal in-memory metrics collector.

Purpose:
    - Counters and simple latency samples for early degradation detection.
    - Zero external deps; can be swapped by Prometheus exporter later.

Core API (intentionally tiny):
    inc(name, labels=None, value=1)
    observe(name, value, labels=None)
    snapshot() -> dict (copy for safe reading)

Thread-safety: coarse RLock; overhead negligible for low event volume.

Harmony / LLM related metric names (documented for discoverability):
    - harmony_parse_error_total{stage}
    - reasoning_ratio_alert_total{bucket}
    - generation_cancelled_total{reason}
    - model_cap_hits_total{model}
    - harmony_unexpected_order_total{type}            # (ADR-0023)
    - commentary_tokens_total{model}                  # (ADR-0024)
    - commentary_retention_mode_total{mode}           # (ADR-0024)
    - commentary_retention_redactions_total           # (ADR-0024)
    - commentary_retention_override_total{from,to}    # (ADR-0025 extension)

Helper functions are provided for newly added ADR-backed metrics to reduce
label spelling drift and ease refactors. They are thin wrappers over ``inc``.
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
        counters: dict[Any, float] = {}
        legacy_counters: dict[tuple[str], float] = {}
        for (name, labels), v in _COUNTERS.items():
            label_str = ""
            if labels:
                label_str = "{" + ",".join(f"{k}={v}" for k, v in labels) + "}"
            # Primary string key representation
            counters[name + label_str] = v
            # Legacy compatibility (ADR-0027): expose tuple key form
            # in separate map.
            legacy_key = (name,)
            legacy_counters[legacy_key] = v
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
            # Provide legacy view explicitly so any remaining legacy tests
            # can migrate without colliding key types in primary mapping.
            "counters_legacy": legacy_counters,
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


# ------------------- Helper wrappers (ADR backed) -------------------

def inc_unexpected_order(order_type: str) -> None:
    """Increment unexpected order anomaly counter.

        order_type: one of:
            - extra_final
            - analysis_after_final
            - commentary_after_final
            - interleaved_final
    (See ADR-0023)
    """
    inc("harmony_unexpected_order_total", {"type": order_type})


def inc_commentary_tokens(model: str, value: int = 1) -> None:
    """Increment commentary token counter (ADR-0024)."""
    if value:
        inc("commentary_tokens_total", {"model": model}, value=value)


def inc_commentary_retention_mode(mode: str) -> None:
    """Increment retention mode selection counter (ADR-0024)."""
    inc("commentary_retention_mode_total", {"mode": mode})


def inc_commentary_redactions(count: int = 1) -> None:
    """Increment redaction occurrences (ADR-0024)."""
    if count:
        inc("commentary_retention_redactions_total", value=count)


__all__ += [
    "inc_unexpected_order",
    "inc_commentary_tokens",
    "inc_commentary_retention_mode",
    "inc_commentary_redactions",
    "inc_tool_commentary_sanitized",
    "inc_commentary_retention_override",
    "inc_perf_guard_skipped_regression",
]


def inc_tool_commentary_sanitized(count: int = 1) -> None:
    """Increment when tool commentary text is sanitized/filtered.

    (ADR-0025 extension)
    """
    if count:
        inc("tool_commentary_sanitized_total", value=count)


def inc_commentary_retention_override(from_mode: str, to_mode: str) -> None:
    """Increment override metric when tool_chain changes retention mode.

    Labels:
        from: base/original mode
        to:   applied override mode

    (ADR-0025 extension)
    """
    if from_mode and to_mode and from_mode != to_mode:
        inc(
            "commentary_retention_override_total",
            {"from": from_mode, "to": to_mode},
        )


def inc_perf_guard_skipped_regression(reason: str, scenario: str) -> None:
    """Metric: a detected perf regression was skipped (temporary policy).

    Labels:
        reason: policy bucket (degenerate|gpu_short|other)
        scenario: scenario id

    Used during temporary relaxation phase; slated for removal when guard
    re-tightened (see 2025-09-06 perf guard relaxation changelog).
    """
    if reason and scenario:
        inc(
            "perf_guard_skipped_regression_total",
            {"reason": reason, "scenario": scenario},
        )
