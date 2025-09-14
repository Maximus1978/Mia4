"""Abort registry for in-flight generation requests.

Thread-safe minimal structure mapping request_id -> aborted flag.
Public API kept tiny to simplify future swap (e.g. to actor mailbox).
"""
from __future__ import annotations

from threading import RLock

_ABORTS: dict[str, bool] = {}
_ABORT_START: dict[str, float] = {}
_LOCK = RLock()


def register(request_id: str) -> None:  # noqa: D401
    with _LOCK:
        _ABORTS[request_id] = False


def abort(request_id: str) -> bool:  # noqa: D401
    with _LOCK:
        if request_id in _ABORTS:
            _ABORTS[request_id] = True
            from time import time as _t
            _ABORT_START.setdefault(request_id, _t())
            return True
        return False


def is_aborted(request_id: str) -> bool:  # noqa: D401
    with _LOCK:
        return _ABORTS.get(request_id, False)


def clear(request_id: str) -> None:  # noqa: D401
    with _LOCK:
        _ABORTS.pop(request_id, None)
        _ABORT_START.pop(request_id, None)


def abort_started_at(request_id: str) -> float | None:  # noqa: D401
    with _LOCK:
        return _ABORT_START.get(request_id)


def mark_start(request_id: str) -> None:  # noqa: D401
    from time import time as _t
    with _LOCK:
        _ABORT_START[request_id] = _t()


__all__ = [
    "register",
    "abort",
    "is_aborted",
    "clear",
    "abort_started_at",
    "mark_start",
]
