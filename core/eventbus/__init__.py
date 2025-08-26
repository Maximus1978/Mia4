"""EventBus v1 (sync in-process) per ADR-0011.

Features:
  - subscribe(event_name, handler)
  - emit(event_name, payload) adds ts if missing
  - handler isolation (exceptions counted, not propagated)
    - metrics counters:
            events_emitted_total{event}, handler_exceptions_total{event},
            dispatch_latency_accum_ms{event}, dispatch_count{event}

No async / filtering / replay yet (planned v2).
"""
from __future__ import annotations

from threading import RLock
from time import time
from typing import Any, Callable, Dict, List

from core import metrics

Handler = Callable[[Dict[str, Any]], None]


class EventBus:
    def __init__(self) -> None:
        self._subs: Dict[str, List[Handler]] = {}
        self._lock = RLock()

    def subscribe(self, event: str, handler: Handler) -> None:
        with self._lock:
            self._subs.setdefault(event, []).append(handler)

    def emit(self, event: str, payload: Dict[str, Any]) -> None:
        t0 = time()
        if "ts" not in payload:
            payload["ts"] = t0
        with self._lock:
            subs = list(self._subs.get(event, ()))
        metrics.inc("events_emitted_total", {"event": event})
        for h in subs:
            try:
                h(dict(payload))  # shallow copy for safety
            except Exception:  # noqa: BLE001
                metrics.inc("handler_exceptions_total", {"event": event})
        latency_ms = int((time() - t0) * 1000)
        metrics.inc(
            "dispatch_latency_accum_ms", {"event": event}, latency_ms
        )
        metrics.inc("dispatch_count", {"event": event})

    def reset_for_tests(self) -> None:  # pragma: no cover
        with self._lock:
            self._subs.clear()


_BUS = EventBus()


def subscribe(event: str, handler: Handler) -> None:
    _BUS.subscribe(event, handler)


def emit(event: str, payload: Dict[str, Any]) -> None:
    _BUS.emit(event, payload)


__all__ = ["emit", "subscribe", "EventBus"]
