"""SSE utilities."""
from __future__ import annotations

from typing import AsyncGenerator, Iterable


def format_event(event: str | None, data: str) -> str:
    lines = []
    if event:
        lines.append(f"event: {event}")
    # data may contain newlines; split per SSE spec
    for line in data.splitlines() or [""]:
        lines.append(f"data: {line}")
    return "\n".join(lines) + "\n\n"


async def wrap_generator(
    gen: Iterable[str],
) -> AsyncGenerator[bytes, None]:  # pragma: no cover - thin adapter
    for chunk in gen:
        yield chunk.encode("utf-8")
