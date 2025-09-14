"""(Legacy slim) n-gram suppression utilities.

Full reasoning/final separation now handled exclusively by
`HarmonyChannelAdapter` in `core.llm.adapters` (streaming incremental
parser of Harmony response format channels). This module remains only
as a provider of the lightweight `_NGramGuard` used by the adapter.

All former marker / buffered Harmony tag splitting logic has been
removed (purged as part of full Harmony migration). Any remaining
imports of `process_stream` should be eliminated; tests have been
updated to rely on the adapter path. Keeping a minimal stub to avoid
ImportError during transitional refactors; will be deleted after all
callers are migrated.
"""
from __future__ import annotations

from collections import deque
from typing import Iterable, Iterator, Dict

# NOTE: metrics no longer required here; leak detection & stats computed in
# HarmonyChannelAdapter.


class _NGramGuard:
    def __init__(self, n: int, window: int) -> None:
        self.n = max(1, n)
        self.window = max(self.n, window)
        self.buf: deque[str] = deque()

    def allow(self, token: str) -> bool:
        # Basic heuristic: if last n-gram equals candidate token repeated
        # (simple immediate duplication), skip. More advanced pattern
        # detection can be added later.
        if not token.strip():
            return True
        if len(self.buf) >= self.n:
            recent = list(self.buf)[-self.n:]
            if all(t == token for t in recent):  # exact repeat n times
                return False
        self.buf.append(token)
        while len(self.buf) > self.window:
            self.buf.popleft()
        return True


def process_stream(
    chunks: Iterable[str], cfg: Dict
) -> Iterator[Dict]:  # noqa: D401
    """Deprecated passthrough (will be removed).

    Emits each chunk as delta then final stats with zeros.

    Kept only to satisfy stale imports during migration. New code must use
    `HarmonyChannelAdapter` which already performs n-gram suppression and
    reasoning/final accounting.
    """
    for c in chunks:
        yield {"type": "delta", "text": c}
    yield {
        "type": "final",
        "stats": {
            "reasoning_tokens": 0,
            "final_tokens": 0,
            "reasoning_ratio": 0.0,
            "drop_from_history": True,
        },
        "reasoning_text": None,
    }


__all__ = ["process_stream", "_NGramGuard"]
