"""Central Error Taxonomy enforcement (ADR-0006)."""
from __future__ import annotations

_ALLOWED_ERROR_TYPES = {
    # model.load
    "file-not-found",
    "checksum-mismatch",
    "incompatible-format",
    "init-timeout",
    "provider-internal",
    # generation.request
    "invalid-params",
    "context-overflow",
    "safety-filtered",
    # generation.runtime
    "provider-error",
    "oom",
    "timeout",
    "aborted",
    "stream-broken",
    # infra
    "event-handler-error",
}


def validate_error_type(code: str) -> str:
    assert (
        code in _ALLOWED_ERROR_TYPES
    ), f"Unknown error_type '{code}' (not in taxonomy)"
    return code


def map_exception(e: Exception, phase: str) -> str:
    name = e.__class__.__name__.lower()
    msg = str(e).lower()
    if phase == "model.load":
        if "not found" in msg:
            return "file-not-found"
        return "provider-internal"
    if phase == "generation":
        if "abort" in name or "cancel" in name:
            return "aborted"
        if "timeout" in name or "timeout" in msg:
            return "timeout"
        return "provider-error"
    return "provider-internal"


__all__ = ["validate_error_type", "map_exception"]
