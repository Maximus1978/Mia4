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
    - reasoning_leak_total{reason}                    # (ADR-CH-SEP-V2)
    - channel_merge_anomaly_total{type}               # (ADR-CH-SEP-V2)
    - fused_marker_sanitizations_total{kind}          # (ADR-0013i addendum)

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


# ------------------- Channel separation (ADR-CH-SEP-V2) --------------
def inc_reasoning_leak(reason: str) -> None:
    """Increment reasoning leak metric.

    reason: classifier for leak source. Suggested values:
        - analysis_in_final
        - post_final_analysis
        - service_marker_in_final
        - mixed_channel_fragment
    """
    if reason:
        inc("reasoning_leak_total", {"reason": reason})


def inc_channel_merge_anomaly(kind: str) -> None:
    """Increment channel merge anomaly metric.

    kind: classifier for anomaly:
        - analysis_token_emitted_as_delta
        - commentary_token_in_final
        - post_finalize_emission
    """
    if kind:
        inc("channel_merge_anomaly_total", {"type": kind})


__all__ += [
    "inc_unexpected_order",
    "inc_commentary_tokens",
    "inc_commentary_retention_mode",
    "inc_commentary_redactions",
    "inc_reasoning_leak",
    "inc_channel_merge_anomaly",
]


def inc_fused_marker_sanitization(kind: str) -> None:
    """Increment fused marker sanitation counter.

    kind: classifier for sanitation path (prefix|residue|other future).
    """
    if kind:
        inc("fused_marker_sanitizations_total", {"kind": kind})


__all__ += ["inc_fused_marker_sanitization"]


# ------------------- Perf guard helpers (future ADR) -------------------
def inc_perf_guard_skipped_regression(reason: str, scenario: str) -> None:
    """Track skipped regression classification for perf guard.

    Allows tests to record why a potential regression was ignored
    (degenerate, gpu_short, etc.) to aid later analysis without failing
    guardrails.
    """
    if reason and scenario:
        inc(
            "perf_guard_skipped_regression_total",
            {"reason": reason, "scenario": scenario},
        )


__all__ += ["inc_perf_guard_skipped_regression"]
