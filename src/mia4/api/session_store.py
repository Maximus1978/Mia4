"""In-memory session store (MVP).

Not a public configurable component: limits are internal constants for Phase 2.
Implements TTL + max messages per session; lazy cleanup on write.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from time import time
from typing import Deque, Dict, List

from core import metrics

MAX_MESSAGES = 50
SESSION_TTL_SECONDS = 60 * 60  # 60 minutes


@dataclass(slots=True)
class ChatMessage:
    role: str  # user|assistant|system
    content: str
    ts: float


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, Deque[ChatMessage]] = {}
        self._last_access: Dict[str, float] = {}

    def add(self, session_id: str, role: str, content: str) -> None:
        now = time()
        q = self._sessions.get(session_id)
        if q is None:
            q = deque(maxlen=MAX_MESSAGES)
            self._sessions[session_id] = q
        q.append(ChatMessage(role=role, content=content, ts=now))
        self._last_access[session_id] = now
        metrics.inc("session_messages_total", {"role": role})
        self._cleanup(now)

    def history(self, session_id: str) -> List[ChatMessage]:
        return list(self._sessions.get(session_id, []))

    def _cleanup(self, now: float) -> None:
        expired = [
            sid
            for sid, ts in self._last_access.items()
            if now - ts > SESSION_TTL_SECONDS
        ]
        for sid in expired:
            self._sessions.pop(sid, None)
            self._last_access.pop(sid, None)

    def stats(self) -> dict:
        return {"sessions": len(self._sessions)}


store = SessionStore()

__all__ = ["store", "SessionStore", "ChatMessage"]
