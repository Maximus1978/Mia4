"""Event dataclasses + legacy any-subscriber bridge (single clean copy).

Preferred: use `core.eventbus` for per-event subscriptions.
This transitional module exposes `subscribe(handler)` where handler(name, payload)
receives every event. Will be removed after migration.
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
class GenerationStarted(BaseEvent):
    request_id: str
    model_id: str
    role: str
    prompt_tokens: int
    parent_request_id: str | None = None
    correlation_id: str | None = None


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
    request_id: str
    mode: str
    temperature: float | None = None
    top_p: float | None = None


_ANY_SUBS: List[EventHandler] = []


def _metrics_collector(name: str, payload: Dict[str, Any]) -> None:  # noqa: D401
    if name in {"GenerationStarted", "GenerationChunk", "GenerationCompleted", "GenerationFailed"}:
        _metrics.inc("events_generation", {"type": name[10:].lower()})
    elif name in {"ModelLoaded", "ModelUnloaded"}:
        _metrics.inc("events_" + name.lower(), {"role": payload.get("role")})
    elif name == "ReasoningPresetApplied":
        _metrics.inc("reasoning_mode", {"mode": payload.get("mode")})


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
    _ANY_SUBS.clear()
    _ANY_SUBS.append(_metrics_collector)


__all__ = [
    "emit",
    "on",
    "subscribe",
    "ModelLoaded",
    "ModelLoadFailed",
    "ModelUnloaded",
    "GenerationStarted",
    "GenerationChunk",
    "GenerationCompleted",
    "GenerationFailed",
    "JudgeInvocation",
    "PlanGenerated",
    "ReasoningPresetApplied",
    "reset_listeners_for_tests",
]
