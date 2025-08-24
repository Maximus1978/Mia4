"""Minimal event bus & event types.

Scope (Step 6.1 focus):
  - ModelLoaded / ModelLoadFailed
  - GenerationStarted / GenerationFinished / GenerationFailed

Design goals:
  - Lightweight in-memory pub/sub (list of subscribers) without external deps
  - Structured payloads via dataclasses for type safety
  - No global hardcoded routing logic beyond a singleton bus (will evolve)
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from threading import RLock
from time import time
from typing import Any, Callable, Dict, List, Protocol
from core import metrics as _metrics

EventHandler = Callable[[str, Dict[str, Any]], None]


class SupportsEvent(Protocol):  # future extensibility marker
  def to_event(self) -> Dict[str, Any]:  # pragma: no cover - protocol
    ...


@dataclass(slots=True)
class BaseEvent:
  def to_event(self) -> Dict[str, Any]:  # noqa: D401
    d = asdict(self)
    d["ts"] = d.get("ts") or time()
    return d


# Lifecycle
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


# Unload
@dataclass(slots=True)
class ModelUnloaded(BaseEvent):
  model_id: str
  role: str
  reason: str
  idle_seconds: int | None = None


# Generation
@dataclass(slots=True)
class GenerationStarted(BaseEvent):
  request_id: str
  model_id: str
  role: str
  prompt_tokens: int
  parent_request_id: str | None = None


@dataclass(slots=True)
class GenerationFinished(BaseEvent):
  request_id: str
  model_id: str
  role: str
  output_tokens: int
  latency_ms: int
  truncated: bool | None = None
  stop_reason: str | None = None


@dataclass(slots=True)
class GenerationFailed(BaseEvent):
  request_id: str
  model_id: str
  role: str
  error_type: str
  message: str | None = None


# Judge / Planning
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
  model_id: str | None = None


# Reasoning presets
@dataclass(slots=True)
class ReasoningPresetApplied(BaseEvent):
  request_id: str
  mode: str
  temperature: float | None = None
  top_p: float | None = None


class EventBus:
  def __init__(self) -> None:
    self._subs: List[EventHandler] = []
    self._lock = RLock()

  def subscribe(self, handler: EventHandler) -> None:
    with self._lock:
      self._subs.append(handler)

  def publish(self, name: str, payload: Dict[str, Any]) -> None:
    # Shallow copy to avoid mutation by handlers
    with self._lock:
      subs = list(self._subs)
    for h in subs:
      try:
        h(name, dict(payload))
      except Exception:  # noqa: BLE001
        # Silently ignore for now; later add logging
        continue


_BUS = EventBus()


# Auto-subscribe metrics collector (minimal counters) so user sees snapshot via metrics.snapshot()
def _metrics_collector(name: str, payload: Dict[str, Any]) -> None:  # noqa: D401
  # Map events to counters
  if name in (
    "GenerationFinished",
    "GenerationFailed",
    "GenerationStarted",
  ):
    _metrics.inc("events_generation", {"type": name[10:].lower()})
  elif name in ("ModelLoaded", "ModelUnloaded"):
    _metrics.inc(
      f"events_{name.lower()}", {"role": payload.get("role")}
    )
  elif name == "ReasoningPresetApplied":
    _metrics.inc("reasoning_mode", {"mode": payload.get("mode")})


_BUS.subscribe(_metrics_collector)


def emit(ev: BaseEvent | SupportsEvent) -> None:
  name = ev.__class__.__name__
  _BUS.publish(name, ev.to_event())


def on(handler: EventHandler) -> None:
  _BUS.subscribe(handler)


def subscribe(handler: EventHandler):  # backward compatible helper
  """Subscribe and return an unsubscribe callable."""
  _BUS.subscribe(handler)

  def _unsub():  # noqa: D401
    try:
      _BUS._subs.remove(handler)  # type: ignore[attr-defined]
    except ValueError:
      pass

  return _unsub


def reset_listeners_for_tests() -> None:  # pragma: no cover - test helper
  _BUS._subs.clear()  # type: ignore[attr-defined]
  # Re-subscribe internal collectors
  _BUS.subscribe(_metrics_collector)


__all__ = [
  "emit",
  "on",
  "subscribe",
  # events
  "ModelLoaded",
  "ModelLoadFailed",
  "ModelUnloaded",
  "GenerationStarted",
  "GenerationFinished",
  "GenerationFailed",
  "JudgeInvocation",
  "PlanGenerated",
  "ReasoningPresetApplied",
  "reset_listeners_for_tests",
]
