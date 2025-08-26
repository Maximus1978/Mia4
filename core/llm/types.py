"""LLM shared result types (S5)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass(slots=True)
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int


@dataclass(slots=True)
class GenerationTimings:
    total_ms: int
    decode_tps: float | None = None


@dataclass(slots=True)
class GenerationError:
    type: str
    message: str | None = None


@dataclass(slots=True)
class GenerationResult:
    version: int
    status: str  # ok | error
    text: str
    usage: TokenUsage
    timings: GenerationTimings
    model_id: str
    role: str
    request_id: str
    error: Optional[GenerationError] = None
    extra: Dict[str, Any] | None = None

    @staticmethod
    def ok(
        text: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_ms: int,
        model_id: str,
        role: str,
        request_id: str,
    ) -> "GenerationResult":
        decode_tps = None
        if completion_tokens and total_ms > 0:
            decode_tps = completion_tokens / (total_ms / 1000)
        return GenerationResult(
            version=2,
            status="ok",
            text=text,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            ),
            timings=GenerationTimings(
                total_ms=total_ms, decode_tps=decode_tps
            ),
            model_id=model_id,
            role=role,
            request_id=request_id,
        )

    @staticmethod
    def failure(
        err_type: str,
        message: str | None,
        prompt_tokens: int,
        completion_tokens: int,
        total_ms: int,
        model_id: str,
        role: str,
        request_id: str,
        text: str = "",
    ) -> "GenerationResult":
        decode_tps = None
        if completion_tokens and total_ms > 0:
            decode_tps = completion_tokens / (total_ms / 1000)
        return GenerationResult(
            version=2,
            status="error",
            text=text,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            ),
            timings=GenerationTimings(
                total_ms=total_ms, decode_tps=decode_tps
            ),
            model_id=model_id,
            role=role,
            request_id=request_id,
            error=GenerationError(type=err_type, message=message),
        )
