"""Event dataclasses + legacy any-subscriber bridge (single clean copy).

Preferred: use `core.eventbus` for per-event subscriptions.
This transitional module exposes `subscribe(handler)` where
handler(name, payload) receives every event. Will be removed after
migration.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from time import time
from typing import Any, Callable, Dict, List, Protocol

from core import metrics as _metrics
from core.eventbus import emit as _emit_bus

EventHandler = Callable[[str, Dict[str, Any]], None]


class SupportsEvent(Protocol):  # pragma: no cover
    def to_event(self) -> Dict[str, Any]:  # noqa: D401
        ...


@dataclass(slots=True)
class BaseEvent:
    def to_event(self) -> Dict[str, Any]:  # noqa: D401
        data = asdict(self)
        data["ts"] = data.get("ts") or time()
        return data


@dataclass(slots=True)
class ModelLoaded(BaseEvent):
    model_id: str
    role: str
    load_ms: int
    revision: str | None = None


@dataclass(slots=True)
class ModelLoadFailed(BaseEvent):
    model_id: str
    role: str
    error_type: str
    message: str | None = None


@dataclass(slots=True)
class ModelUnloaded(BaseEvent):
    model_id: str
    role: str
    reason: str
    idle_seconds: int | None = None


@dataclass(slots=True)
class ModelAliasedLoaded(BaseEvent):
    alias_id: str
    base_id: str
    role: str
    base_role: str
    reuse: bool = True


@dataclass(slots=True)
class ModelDowngraded(BaseEvent):
    model_id: str
    role: str
    reason: str  # e.g. low_vram
    free_vram_mb_before: int | None = None


@dataclass(slots=True)
class GenerationStarted(BaseEvent):
    request_id: str
    model_id: str
    role: str
    prompt_tokens: int
    parent_request_id: str | None = None
    correlation_id: str | None = None
    system_prompt_version: int | None = None
    system_prompt_hash: str | None = None
    persona_len: int | None = None
    sampling: dict | None = None  # optional sampling params snapshot
    sampling_origin: str | None = None  # passport|preset|user|mixed
    merged_sampling: dict | None = None  # final merged values (normalized)
    # effective stop sequences (if any)
    stop_sequences: list[str] | None = None
    cap_applied: bool | None = None  # True если max_tokens был урезан
    # паспортным лимитом


@dataclass(slots=True)
class GenerationChunk(BaseEvent):
    request_id: str
    model_id: str
    role: str
    correlation_id: str
    seq: int  # 0-based
    text: str
    tokens_out: int  # cumulative produced tokens


@dataclass(slots=True)
class GenerationCompleted(BaseEvent):
    request_id: str
    model_id: str
    role: str
    status: str  # ok|error
    correlation_id: str
    output_tokens: int
    latency_ms: int
    result_summary: dict | None = None
    error_type: str | None = None
    message: str | None = None
    stop_reason: str | None = None
    sampling_origin: str | None = None
    merged_sampling: dict | None = None


@dataclass(slots=True)
class GenerationCancelled(BaseEvent):
    """Generation cancelled mid-flight (user abort or timeout)."""
    request_id: str
    model_id: str
    role: str
    reason: str  # user_abort|timeout
    latency_ms: int
    output_tokens: int
    correlation_id: str | None = None
    message: str | None = None


@dataclass(slots=True)
class CancelLatencyMeasured(BaseEvent):
    """End-to-end user cancel latency measurement.

    duration_ms: total time from abort receipt to SSE end.
    path: abort path (user_abort|timeout); only user_abort measured.
    """
    request_id: str
    model_id: str | None
    duration_ms: int
    path: str


@dataclass(slots=True)
class GenerationFailed(BaseEvent):  # deprecated
    request_id: str
    model_id: str
    role: str
    error_type: str
    message: str | None = None


@dataclass(slots=True)
class JudgeInvocation(BaseEvent):
    request_id: str
    model_id: str
    target_request_id: str
    agreement: float | None = None


@dataclass(slots=True)
class PlanGenerated(BaseEvent):
    request_id: str
    steps_count: int
    model_id: str


@dataclass(slots=True)
class ReasoningPresetApplied(BaseEvent):
    """Reasoning preset selection (v2).

    preset: preset name (low|medium|high|custom future)
    mode: baseline|overridden (whether user overrides changed preset fields)
    overridden_fields: list of keys changed by user overrides (if any)
    """
    request_id: str
    preset: str
    mode: str  # baseline|overridden
    temperature: float | None = None
    top_p: float | None = None
    overridden_fields: list[str] | None = None


@dataclass(slots=True)
class ModelRouted(BaseEvent):
    """Model routing decision snapshot.

    Emitted after pipeline selection but before streaming starts.
    capabilities: optional dict like {"tool_calls": bool,
    "reasoning_split": bool}
    """
    request_id: str
    model_id: str
    pipeline: str  # primary|lightweight|...
    capabilities: dict | None = None


@dataclass(slots=True)
class ModelPassportMismatch(BaseEvent):
    """Passport vs config mismatch (warning).

    Emitted when model passport declared limits diverge from configured
    limits (e.g. max_output_tokens). Allows surfacing drift.
    field: which field mismatched (currently only max_output_tokens).
    passport_value / config_value: numeric values observed.
    """
    model_id: str
    field: str
    passport_value: int | None
    config_value: int | None


@dataclass(slots=True)
class ToolCallPlanned(BaseEvent):
    """Planned tool call (MVP no-op execution).

    args_preview_hash: privacy-preserving hash of truncated canonical args.
    seq: order within the request (0-based).
    """
    request_id: str
    tool: str
    args_preview_hash: str
    seq: int
    args_schema_version: str | None = None


@dataclass(slots=True)
class ToolCallResult(BaseEvent):
    """Result of tool call (synthetic immediate for MVP).

    status: ok|error
    latency_ms: synthetic latency (0-1ms typical for stub)
    error_type/message only on failure.
    """
    request_id: str
    tool: str
    status: str
    latency_ms: int
    seq: int
    error_type: str | None = None
    message: str | None = None


@dataclass(slots=True)
class ReasoningSuppressedOrNone(BaseEvent):
    """No reasoning content emitted.

    Emitted when generation completes without any reasoning tokens:
    - either because drop_history flag suppresses it, or
    - model produced zero analysis tokens.
    reason: no-analysis-channel | drop_history | both
    request_id: correlation with generation
    model_id: model used
    final_tokens: produced final tokens count
    """
    request_id: str
    model_id: str
    reason: str
    final_tokens: int


_ANY_SUBS: List[EventHandler] = []
# Generation counter used by tests: each call to reset_listeners_for_tests
# increments this so already-loaded providers can re-emit ModelLoaded when
# first accessed in a new test without needing to fully reload weights.
_EVENT_GENERATION = 0


def get_event_generation() -> int:  # pragma: no cover - lightweight helper
    return _EVENT_GENERATION


def _metrics_collector(
    name: str, payload: Dict[str, Any]
) -> None:  # noqa: D401
    gen_names = {
        "GenerationStarted",
        "GenerationChunk",
        "GenerationCompleted",
        "GenerationFailed",
        "GenerationCancelled",
    }
    if name in gen_names:
        _metrics.inc("events_generation", {"type": name[10:].lower()})
    elif name in {"ModelLoaded", "ModelUnloaded"}:
        _metrics.inc("events_" + name.lower(), {"role": payload.get("role")})
    elif name == "ModelAliasedLoaded":
        _metrics.inc(
            "model_provider_reuse_total",
            {"role": payload.get("role")},
        )
    elif name == "ModelDowngraded":
        _metrics.inc(
            "model_downgraded_total",
            {"reason": payload.get("reason", "unknown")},
        )
    elif name == "ReasoningPresetApplied":
        _metrics.inc("reasoning_mode", {"mode": payload.get("mode")})
    elif name == "ModelPassportMismatch":
        _metrics.inc(
            "model_passport_mismatch_total",
            {"field": payload.get("field", "unknown")},
        )
    elif name == "CancelLatencyMeasured":
        _metrics.observe(
            "cancel_latency_ms",
            payload.get("duration_ms", 0),
            {"path": payload.get("path", "unknown")},
        )
    # debug counter to ensure path executed (can be removed later)
        _metrics.inc(
            "cancel_latency_events_total",
            {"path": payload.get("path", "unknown")},
        )
    elif name == "ToolCallResult":
        # Increment frequency counter with status label
        _metrics.inc(
            "tool_calls_total",
            {
                "tool": payload.get("tool", "unknown"),
                "status": payload.get("status", "unknown"),
            },
        )
        # Observe latency histogram
        _metrics.observe(
            "tool_call_latency_ms",
            payload.get("latency_ms", 0),
            {"tool": payload.get("tool", "unknown")},
        )
    elif name == "ReasoningSuppressedOrNone":
        _metrics.inc(
            "reasoning_none_total",
            {"reason": payload.get("reason", "unknown")},
        )


_ANY_SUBS.append(_metrics_collector)


def emit(ev: BaseEvent | SupportsEvent) -> None:
    name = ev.__class__.__name__
    payload = ev.to_event()
    _emit_bus(name, payload)
    for h in list(_ANY_SUBS):  # copy for isolation
        try:
            h(name, dict(payload))
        except Exception:  # noqa: BLE001
            _metrics.inc("handler_exceptions_total", {"event": name})


def on(handler: EventHandler) -> None:
    _ANY_SUBS.append(handler)


def subscribe(handler: EventHandler):  # backward compatible helper
    on(handler)

    def _unsub() -> None:  # noqa: D401
        try:
            _ANY_SUBS.remove(handler)
        except ValueError:
            pass
    return _unsub


def reset_listeners_for_tests() -> None:  # pragma: no cover
    global _EVENT_GENERATION  # noqa: PLW0603
    _ANY_SUBS.clear()
    _ANY_SUBS.append(_metrics_collector)
    # Bump generation so cached providers know to re-emit ModelLoaded
    _EVENT_GENERATION += 1


__all__ = [
    "emit",
    "on",
    "subscribe",
    "ModelLoaded",
    "ModelLoadFailed",
    "ModelUnloaded",
    "ModelAliasedLoaded",
    "ModelDowngraded",
    "GenerationStarted",
    "GenerationChunk",
    "GenerationCompleted",
    "GenerationFailed",
    "GenerationCancelled",
    "JudgeInvocation",
    "PlanGenerated",
    "ReasoningPresetApplied",
    "CancelLatencyMeasured",
    "ModelPassportMismatch",
    "ToolCallPlanned",
    "ToolCallResult",
    "ReasoningSuppressedOrNone",
    "reset_listeners_for_tests",
    "get_event_generation",
]
