"""/generate route: streaming with reasoning split & stop sequence support."""
from __future__ import annotations

import json
import os
import time
import traceback
import uuid
from fastapi import APIRouter, HTTPException
import threading
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core import metrics
from core.config import get_config
from core.events import (
    GenerationCompleted,
    GenerationCancelled,
    ReasoningPresetApplied,
    CancelLatencyMeasured,
    ToolCallPlanned,
    ToolCallResult,
    emit,
)
from core.events import ModelPassportMismatch  # explicit for stream warning
from core.events import subscribe
from core.llm.factory import apply_reasoning_overrides, get_model
from core.llm.pipeline.primary import PrimaryPipeline
from mia4.api.session_store import store
from mia4.api.sse import format_event
from mia4.api import abort_registry

router = APIRouter()


class GenerateOverrides(BaseModel):  # noqa: D401
    reasoning_preset: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    max_output_tokens: int | None = Field(None, alias="max_output_tokens")
    top_k: int | None = None
    repeat_penalty: float | None = None
    min_p: float | None = None
    typical_p: float | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    repeat_last_n: int | None = None
    penalize_nl: bool | None = None
    seed: int | None = None
    mirostat: int | None = None
    mirostat_tau: float | None = None
    mirostat_eta: float | None = None
    n_gpu_layers: int | str | None = None
    generation_timeout_s: float | None = None
    generation_initial_idle_grace_s: float | None = None
    dev_pre_stream_delay_ms: float | None = None
    dev_per_token_delay_ms: float | None = None
    stop: list[str] | None = None


class GenerateRequest(BaseModel):  # noqa: D401
    session_id: str
    model: str
    prompt: str
    overrides: GenerateOverrides | None = None


def _generation_timeout_s() -> int:
    try:
        cfg = get_config().llm
        if cfg and getattr(cfg, "generation_timeout_s", None):
            return cfg.generation_timeout_s
    except Exception:  # noqa: BLE001
        pass
    return 120


def _generation_initial_idle_grace_s() -> float:
    try:
        cfg = get_config().llm
        if cfg and getattr(
            cfg, "generation_initial_idle_grace_s", None
        ) is not None:
            raw = getattr(cfg, "generation_initial_idle_grace_s")
            val = float(raw)
            return max(0.0, val)
    except Exception:  # noqa: BLE001
        pass
    return 0.0


def _record_reasoning_ratio_alert(
    model_id: str, ratio: float, llm_conf_root
) -> None:
    try:
        if hasattr(llm_conf_root, "postproc"):
            root_post = getattr(llm_conf_root, "postproc")
            if isinstance(root_post, dict):
                reasoning_cfg = root_post.get("reasoning", {})
            else:
                reasoning_cfg = getattr(root_post, "reasoning", {})
            if not isinstance(reasoning_cfg, dict):
                try:
                    reasoning_cfg = reasoning_cfg.dict()
                except Exception:  # noqa: BLE001
                    reasoning_cfg = {}
            threshold_raw = reasoning_cfg.get("ratio_alert_threshold", 0.45)
        else:
            threshold_raw = 0.45
        threshold = float(threshold_raw)
    except Exception:  # noqa: BLE001
        threshold = 0.45
    if threshold < 0.0:
        threshold = 0.0
    if threshold > 1.0:
        threshold = 1.0
    if ratio < 0.0:
        ratio = 0.0
    if ratio > 1.0:
        ratio = 1.0
    metrics.inc(
        "reasoning_ratio_alert_total",
        {
            "model": model_id,
            "bucket": "above" if ratio > threshold else "below",
        },
    )


@router.post("/generate")
def generate(req: GenerateRequest):  # noqa: D401
    session_id = req.session_id
    model_id = req.model
    if not req.prompt.strip():  # Empty prompt guard
        raise HTTPException(status_code=400, detail="prompt-empty")
    store.add(session_id, "user", req.prompt)

    request_id = str(uuid.uuid4())
    abort_registry.register(request_id)
    abort_started_at = None  # set if/when abort endpoint invoked
    t0 = time.time()
    is_test_mode = os.environ.get("MIA_TEST_MODE") == "1"
    reasoning_mode = req.overrides.reasoning_preset if req.overrides else None
    # Only supported modes: low | medium | high (passport).
    # Any legacy value is rejected.
    if reasoning_mode is not None:
        norm_mode = reasoning_mode.lower()
        if norm_mode not in {"low", "medium", "high"}:
            raise HTTPException(
                status_code=400, detail="invalid-reasoning-preset"
            )
        effective_reasoning_mode = norm_mode
    else:
        effective_reasoning_mode = None
    metrics.inc("sse_stream_open_total", {"model": model_id})

    # Collect user overrides
    user_sampling: dict[str, object] = {}
    requested_gpu_layers_override: object | None = None
    if req.overrides:
        for k in (
            "temperature",
            "top_p",
            "max_output_tokens",
            "top_k",
            "repeat_penalty",
            "min_p",
            "typical_p",
            "presence_penalty",
            "frequency_penalty",
            "repeat_last_n",
            "penalize_nl",
            "seed",
            "mirostat",
            "mirostat_tau",
            "mirostat_eta",
            "n_gpu_layers",
            "stop",
        ):
            v = getattr(req.overrides, k, None)
            if v is None:
                continue
            if k == "max_output_tokens":
                user_sampling["max_tokens"] = v
            elif k == "stop" and isinstance(v, list) and v:
                user_sampling["stop"] = v
            elif k == "n_gpu_layers":
                requested_gpu_layers_override = v
                user_sampling[k] = v
            else:
                user_sampling[k] = v

    # Acquire provider
    try:
        provider = get_model(model_id, repo_root=".")
    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc()
        err_payload = {
            "error_type": "provider-acquire",
            "message": str(e),
            "phase": "pre_stream",
            "model_id": model_id,
            "request_id": request_id,
        }
        print("PRESTREAM_ERROR", json.dumps(err_payload), "TRACE", tb)
        raise HTTPException(status_code=500, detail=err_payload) from e

    # GPU layer override handling -----------------------------------------
    gpu_layers_state: dict[str, object] = {}
    gpu_layers_effective: int | None = None
    gpu_layers_requested: object | None = None
    gpu_layers_fallback = False
    gpu_offload = False
    warn_events: list[tuple[str, dict[str, object]]] = []
    fallback_warning_emitted = False
    setter = getattr(provider, "set_n_gpu_layers", None)
    getter_effective = getattr(provider, "get_effective_n_gpu_layers", None)
    getter_requested = getattr(provider, "get_requested_n_gpu_layers", None)
    if requested_gpu_layers_override is not None:
        if not callable(setter):
            raise HTTPException(
                status_code=400,
                detail={"error_type": "n_gpu_layers-unsupported"},
            )
        try:
            gpu_layers_state = setter(requested_gpu_layers_override) or {}
        except ValueError as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=400,
                detail={"error_type": "invalid-n_gpu_layers"},
            ) from exc
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            err_payload = {
                "error_type": "gpu-layer-update-failed",
                "message": str(exc),
                "requested": requested_gpu_layers_override,
            }
            raise HTTPException(status_code=500, detail=err_payload) from exc
    if gpu_layers_state:
        eff_val = gpu_layers_state.get("effective")
        if isinstance(eff_val, (int, float)):
            gpu_layers_effective = int(eff_val)
        elif eff_val is None:
            gpu_layers_effective = None
        else:
            # Preserve sentinel values like -1 if provided as str
            try:
                gpu_layers_effective = int(eff_val)  # type: ignore[arg-type]
            except Exception:  # noqa: BLE001
                gpu_layers_effective = None
        gpu_layers_requested = gpu_layers_state.get("requested")
        gpu_layers_fallback = bool(gpu_layers_state.get("fallback"))
    if callable(getter_effective) and gpu_layers_effective is None:
        try:
            gpu_layers_effective = getter_effective()
        except Exception:  # noqa: BLE001
            gpu_layers_effective = None
    if callable(getter_requested) and gpu_layers_requested is None:
        try:
            gpu_layers_requested = getter_requested()
        except Exception:  # noqa: BLE001
            gpu_layers_requested = None
    if (
        gpu_layers_requested is None
        and requested_gpu_layers_override is not None
    ):
        gpu_layers_requested = requested_gpu_layers_override
    gpu_offload = bool(
        gpu_layers_effective is not None and gpu_layers_effective > 0
    )
    if (
        gpu_layers_effective in (None, 0)
        and gpu_layers_requested not in (None, "auto", 0)
    ):
        gpu_layers_fallback = True
    if gpu_layers_fallback:
        warn_events.append(
            (
                "warning",
                {
                    "event": "GpuFallback",
                    "request_id": request_id,
                    "model_id": model_id,
                    "requested": gpu_layers_requested,
                    "effective": gpu_layers_effective,
                },
            )
        )

    # Merge sampling layers: passport -> preset -> user
    sampling_origin_layers: list[str] = []
    effective_sampling: dict[str, object] = {}
    passport_defaults: dict[str, object] = {}
    try:
        meta = getattr(provider.info(), "metadata", {}) or {}
        passport_defaults = meta.get("passport_sampling_defaults", {}) or {}
        if passport_defaults:
            sampling_origin_layers.append("passport")
    except Exception:  # noqa: BLE001
        passport_defaults = {}
    for k, v in passport_defaults.items():
        if v is not None:
            effective_sampling[k] = v

    preset_vals: dict[str, object] = {}
    preset_name: str | None = None
    reasoning_max_tokens_preset: int | None = None
    if effective_reasoning_mode:
        sampling_origin_layers.append("preset")
        try:
            preset_vals = apply_reasoning_overrides(
                {}, effective_reasoning_mode
            )
            preset_name = reasoning_mode
            # Extract reasoning_max_tokens separately (not a generation param)
            try:
                presets_dict = get_config().llm.reasoning_presets
                if effective_reasoning_mode in presets_dict:
                    preset_obj = presets_dict[effective_reasoning_mode]
                    # Pydantic object: use getattr or direct access
                    reasoning_max_tokens_preset = getattr(
                        preset_obj, "reasoning_max_tokens", None
                    )
            except Exception:  # noqa: BLE001
                pass
        except KeyError:
            preset_vals = {}
        for k, v in preset_vals.items():
            effective_sampling[k] = v

    overridden_fields: list[str] = []
    if user_sampling:
        sampling_origin_layers.append("user")
        for k, v in user_sampling.items():
            # track overrides relative to preset values
            if k in preset_vals and preset_vals.get(k) != v:
                overridden_fields.append(k)
            effective_sampling[k] = v
    if (
        gpu_layers_requested is not None
        and "n_gpu_layers" not in effective_sampling
    ):
        effective_sampling["n_gpu_layers"] = gpu_layers_requested

    # Emit ReasoningPresetApplied after merging to know overridden fields
    if preset_name:
        emit(
            ReasoningPresetApplied(
                request_id=request_id,
                preset=preset_name,
                mode=(
                    "overridden" if overridden_fields else "baseline"
                ),
                temperature=effective_sampling.get("temperature"),
                top_p=effective_sampling.get("top_p"),
                overridden_fields=overridden_fields or None,
            )
        )

    if not sampling_origin_layers:
        sampling_origin = None
    elif len(sampling_origin_layers) == 1:
        sampling_origin = sampling_origin_layers[0]
    else:
        sampling_origin = "mixed"
    base_kwargs = dict(effective_sampling)
    if gpu_layers_requested is not None:
        base_kwargs["n_gpu_layers"] = gpu_layers_requested

    # Cap logic delegated to pipeline.prepare (ADR-0028)

    # Pipeline prepare (phase 1 extraction, ADR-0026)
    pipeline = PrimaryPipeline()
    ctx = pipeline.prepare(
        request_id=request_id,
        model_id=model_id,
        provider=provider,
        prompt=req.prompt,
        session_messages=[
            (m.role, m.content)
            for m in store.history(session_id)
        ],
        reasoning_mode=effective_reasoning_mode,
        user_sampling=base_kwargs,  # already merged passport/preset/user
        passport_defaults=passport_defaults,
        sampling_origin=sampling_origin,
        reasoning_max_tokens=reasoning_max_tokens_preset,
    )
    # ctx.prompt already harmony-framed; no separate variable needed
    prompt_tokens = ctx.prompt_tokens
    cap_applied = ctx.cap_applied
    effective_max_tokens = ctx.effective_max_tokens
    # cap_source via ctx.cap_source if needed for SSE
    minimal_mode = False
    # No system prompt echo removal needed; pipeline already framed content.
    base_sp_effective = ""
    base_kwargs = ctx.merged_sampling or base_kwargs

    def _strip_echo(sp: str, up: str, text: str) -> str:  # noqa: D401
        """Remove large prompt/system echo & instruction blocks.

        Heuristics:
        1. Strip leading system prompt (up to 2 times) if echoed.
        2. Drop lines with '[REASONING SPLIT]' or starting with '[LEVEL]'.
        3. Remove duplicate leading user prompt.
        4. Trim leading blanks.
        Only affects beginning of output.
        """
        if not text:
            return text
        sp_norm = (sp or "").strip()
        up_norm = (up or "").strip()
        out = text
        # Strip repeated system prompt at start (multi-pass up to 2x)
        for _ in range(2):
            if sp_norm and out.lower().startswith(sp_norm.lower()[:120]):
                # Remove exact system prompt slice if present verbatim
                if out.startswith(sp_norm):
                    out = out[len(sp_norm):]
                else:
                    # Fallback: cut first len(sp_norm) chars anyway (heuristic)
                    out = out[len(sp_norm):]
                out = out.lstrip()
            else:
                break
        # Remove leading user prompt echoes (rare but happens with stub)
        for _ in range(2):
            if up_norm and out.lower().startswith(up_norm.lower()):
                out = out[len(up_norm):].lstrip()
            else:
                break
        # Drop instruction lines
        cleaned_lines = []
        for ln in out.splitlines():
            lstrip = ln.strip()
            if not cleaned_lines and not lstrip:
                continue  # skip leading blank
            if "[REASONING SPLIT]" in lstrip or lstrip.startswith("[LEVEL]"):
                continue
            cleaned_lines.append(ln)
        out = "\n".join(cleaned_lines).lstrip()
        return out

    def _iter():  # noqa: D401
        nonlocal gpu_layers_effective
        nonlocal gpu_layers_requested
        nonlocal gpu_offload
        nonlocal gpu_layers_fallback
        nonlocal fallback_warning_emitted
        nonlocal abort_started_at
        seq = 0
        tokens_out = 0
        # locals
        first_sent = False
        cancel_latency_emitted = False
        generation_cancel_emitted = False
        fragments: list[str] = []
        reasoning_text: str | None = None
        reasoning_stats: dict | None = None
        ratio_alert_recorded = False
        reasoning_final_detect_ts = None
        stop_hit = None
        llm_conf_root = get_config().llm
        timeout_override = (
            req.overrides.generation_timeout_s
            if (
                req.overrides
                and req.overrides.generation_timeout_s is not None
            )
            else None
        )
        initial_grace_override = (
            req.overrides.generation_initial_idle_grace_s
            if (
                req.overrides
                and (
                    req.overrides.generation_initial_idle_grace_s
                    is not None
                )
            )
            else None
        )
        stop_sequences = base_kwargs.get("stop") or []
        t_start = t0
        timeout_s = float(timeout_override or _generation_timeout_s())
        initial_grace_s = float(
            initial_grace_override
            if initial_grace_override is not None
            else _generation_initial_idle_grace_s()
        )
        if initial_grace_s < 0:
            initial_grace_s = 0.0
        last_activity = t_start
        prefirst_grace_logged = False
        # Emit an immediate meta frame so clients can obtain request_id early
        if is_test_mode:
            try:
                yield format_event(
                    "meta",
                    json.dumps({
                        "request_id": request_id,
                        "model_id": model_id,
                        "status": "starting",
                    }),
                )
            except Exception:  # noqa: BLE001
                pass
        for evt_name, payload in warn_events:
            if payload.get("event") == "GpuFallback":
                fallback_warning_emitted = True
            try:
                yield format_event(evt_name, json.dumps(payload))
            except Exception:  # noqa: BLE001
                pass
        try:
            # If abort was already signaled before streaming starts, capture ts
            if (
                abort_registry.is_aborted(request_id)
                and abort_started_at is None
            ):
                abort_started_at = (
                    abort_registry.abort_started_at(request_id)
                    or time.time()
                )
                if is_test_mode:
                    print(
                        "DEBUG_ABORT_DETECTED",
                        request_id,
                        "phase",
                        "pre-start",
                    )
                raise RuntimeError("aborted")
            # (heartbeat removed in refactor; early abort spin below)
            # Optional dev pre-stream delay to allow client-side abort wiring
            if is_test_mode:
                try:
                    _dev_delay_ms = 0
                    if req.overrides and (
                        req.overrides.dev_pre_stream_delay_ms is not None
                        or req.overrides.dev_per_token_delay_ms is not None
                    ):
                        # Fixed 200ms to allow test/client to obtain request_id
                        # and signal abort deterministically.
                        _dev_delay_ms = 200
                    if _dev_delay_ms:
                        time.sleep(_dev_delay_ms / 1000.0)
                except Exception:  # noqa: BLE001
                    pass
            # Emit non-blocking warning about passport/config mismatch
            # (UI toast)
            try:
                primary_limit = None
                try:
                    llm_primary = getattr(get_config().llm, "primary", None)
                    if llm_primary is not None:
                        primary_limit = getattr(
                            llm_primary, "max_output_tokens", None
                        )
                except Exception:  # noqa: BLE001
                    primary_limit = None
                passport_max = None
                try:
                    passport_max = (
                        passport_defaults.get("max_output_tokens")
                        if isinstance(passport_defaults, dict)
                        else None
                    )
                except Exception:  # noqa: BLE001
                    passport_max = None
                if (
                    isinstance(passport_max, (int, float))
                    and isinstance(primary_limit, (int, float))
                    and int(passport_max) != int(primary_limit)
                ):
                    yield format_event(
                        "warning",
                        json.dumps(
                            {
                                "event": "ModelPassportMismatch",
                                "request_id": request_id,
                                "model_id": model_id,
                                "field": "max_output_tokens",
                                "passport_value": int(passport_max),
                                "config_value": int(primary_limit),
                            }
                        ),
                    )
            except Exception:  # noqa: BLE001
                pass
            # Early quick abort check loop (allow client to signal abort)
            for _spin in range(50):  # ~100ms window
                if abort_registry.is_aborted(request_id):
                    if abort_started_at is None:
                        abort_started_at = (
                            abort_registry.abort_started_at(request_id)
                            or time.time()
                        )
                    print("DEBUG_ABORT_DETECTED", request_id, "phase", "spin")
                    raise RuntimeError("aborted")
                time.sleep(0.002)
            first_token_latency_ms: float | None = None
            for evt in pipeline.stream(ctx):
                # Abort & timeout checks
                now = time.time()
                if abort_registry.is_aborted(request_id):
                    # Try to reuse earlier mark_start timestamp if available
                    if abort_started_at is None:
                        abort_started_at = (
                            abort_registry.abort_started_at(request_id)
                            or time.time()
                        )
                    if is_test_mode:
                        print(
                            "DEBUG_ABORT_DETECTED",
                            request_id,
                            "phase",
                            "in-stream",
                        )
                    raise RuntimeError("aborted")
                if (now - last_activity) > timeout_s:
                    idle_span = now - last_activity
                    if (not first_sent) and initial_grace_s > 0:
                        total_prefirst = now - t_start
                        if total_prefirst <= timeout_s + initial_grace_s:
                            if not prefirst_grace_logged:
                                prefirst_grace_logged = True
                                try:
                                    metrics.inc(
                                        "generation_timeout_grace_total",
                                        {"phase": "prefirst"},
                                    )
                                except Exception:  # noqa: BLE001
                                    pass
                            time.sleep(0.05)
                            continue
                    raise TimeoutError(
                        (
                            "generation-timeout "
                            f"idle={idle_span:.3f}s limit={timeout_s:.3f}s"
                        )
                    )
                etype = evt.get("type")
                if etype == "delta":
                    tok = evt.get("text", "")
                    if stop_sequences and tok:
                        for sseq in stop_sequences:
                            if tok.endswith(sseq):
                                stop_hit = sseq
                                tok = tok[: -len(sseq)]
                                if not tok:
                                    break
                    if not tok:
                        last_activity = now
                        continue
                    tokens_out += 1
                    fragments.append(tok)
                    payload = {
                        "seq": seq,
                        "text": tok,
                        "tokens_out": tokens_out,
                        "request_id": request_id,
                        "model_id": model_id,
                    }
                    seq += 1
                    if not first_sent:
                        first_token_latency_ms = (
                            (time.time() - t_start) * 1000.0
                        )
                        metrics.observe(
                            "generation_first_token_latency_ms",
                            first_token_latency_ms,
                            {"model": model_id},
                        )
                        first_sent = True
                    try:
                        metrics.inc(
                            "harmony_channel_tokens_total",
                            {"model": model_id, "channel": "final"},
                        )
                    except Exception:  # noqa: BLE001
                        pass
                    yield format_event("token", json.dumps(payload))
                    last_activity = now
                elif etype == "analysis":
                    atok = evt.get("text", "")
                    if atok:
                        try:
                            metrics.inc(
                                "harmony_channel_tokens_total",
                                {"model": model_id, "channel": "analysis"},
                            )
                        except Exception:  # noqa: BLE001
                            pass
                        yield format_event(
                            "analysis",
                            json.dumps(
                                {
                                    "request_id": request_id,
                                    "model_id": model_id,
                                    "text": atok,
                                }
                            ),
                        )
                    last_activity = now
                elif etype == "commentary":
                    ctext = evt.get("text", "")
                    if ctext:
                        try:
                            metrics.inc(
                                "harmony_channel_tokens_total",
                                {"model": model_id, "channel": "commentary"},
                            )
                        except Exception:  # noqa: BLE001
                            pass
                        yield format_event(
                            "commentary",
                            json.dumps(
                                {
                                    "request_id": request_id,
                                    "model_id": model_id,
                                    "text": ctext,
                                }
                            ),
                        )
                    last_activity = now
                elif etype == "tool_channel_raw":
                    raw = evt.get("raw", "")
                    if not raw:
                        last_activity = now
                        continue
                    # Attempt JSON parse & synthetic execution (config-driven)
                    import hashlib as _hashlib
                    import json as _json
                    seq_tool = seq
                    tool_name = "unknown"
                    status = "ok"
                    err_type = None
                    msg = None
                    latency_ms = 0
                    tc_cfg = getattr(
                        llm_conf_root, "tool_calling", {}
                    ) if llm_conf_root else {}
                    max_payload = int(tc_cfg.get("max_payload_bytes", 8192))
                    retention_cfg = tc_cfg.get("retention", {})
                    retention_mode = retention_cfg.get(
                        "mode", "metrics_only"
                    )
                    hash_preview_max = int(
                        retention_cfg.get(
                            "hash_preview_max_chars", 200
                        )
                    )
                    preview_hash = ""
                    preview_src = None
                    try:
                        if len(raw) > max_payload:
                            raise ValueError("tool_payload_too_large")
                        data = _json.loads(raw)
                        tool_name = (
                            data.get("tool")
                            or data.get("name")
                            or "unknown"
                        )
                        args_obj = (
                            data.get("arguments")
                            or data.get("args")
                            or {}
                        )
                        preview_src_full = _json.dumps(
                            args_obj, sort_keys=True
                        )
                        preview_src = preview_src_full[:hash_preview_max]
                        preview_hash = _hashlib.sha256(
                            preview_src.encode("utf-8")
                        ).hexdigest()[:32]
                        emit(
                            ToolCallPlanned(
                                request_id=request_id,
                                tool=tool_name,
                                args_preview_hash=preview_hash,
                                seq=seq_tool,
                            )
                        )
                    except ValueError as ve:
                        status = "error"
                        err_type = str(ve)
                        msg = str(ve)
                        preview_hash = "err"
                        emit(
                            ToolCallPlanned(
                                request_id=request_id,
                                tool=tool_name,
                                args_preview_hash=preview_hash,
                                seq=seq_tool,
                            )
                        )
                    except Exception as ve:  # noqa: BLE001
                        status = "error"
                        err_type = "tool_payload_parse_error"
                        msg = str(ve)
                        preview_hash = "err"
                        emit(
                            ToolCallPlanned(
                                request_id=request_id,
                                tool=tool_name,
                                args_preview_hash=preview_hash,
                                seq=seq_tool,
                            )
                        )
                    emit(
                        ToolCallResult(
                            request_id=request_id,
                            tool=tool_name,
                            status=status,
                            latency_ms=latency_ms,
                            seq=seq_tool,
                            error_type=err_type,
                            message=msg,
                        )
                    )
                    # Outward commentary representation (retention shaping)
                    try:
                        metrics.inc(
                            "harmony_channel_tokens_total",
                            {"model": model_id, "channel": "commentary"},
                        )
                    except Exception:  # noqa: BLE001
                        pass
                    tool_payload = {
                        "tool": tool_name,
                        "status": status,
                        "ok": status == "ok",
                        "error_type": err_type,
                        "message": msg,
                    }
                    if retention_mode == "hashed_slice":
                        tool_payload["preview_hash"] = preview_hash
                    elif retention_mode == "redacted_snippets":
                        tool_payload["preview_hash"] = preview_hash
                        tool_payload["args_redacted"] = retention_cfg.get(
                            "redacted_placeholder", "[REDACTED]"
                        )
                    elif retention_mode == "raw_ephemeral":
                        tool_payload["preview_hash"] = preview_hash
                        tool_payload["raw_args"] = preview_src
                    yield format_event(
                        "commentary",
                        json.dumps(
                            {
                                "request_id": request_id,
                                "model_id": model_id,
                                "text": json.dumps(tool_payload),
                            }
                        ),
                    )
                    last_activity = now
                elif etype == "final":
                    reasoning_text = evt.get("reasoning_text")
                    # Adapter may provide sanitized final_text (SSOT)
                    final_text_adapter = evt.get("final_text")
                    if final_text_adapter:
                        try:
                            ctx.fragments = [final_text_adapter]
                            ctx.sanitized_final_text = final_text_adapter
                        except Exception:  # noqa: BLE001
                            pass
                    reasoning_stats = evt.get("stats") or {}
                    reasoning_final_detect_ts = evt.get("final_detect_time")
                    try:
                        if reasoning_stats and not ratio_alert_recorded:
                            ratio = reasoning_stats.get("reasoning_ratio")
                            if ratio is not None:
                                _record_reasoning_ratio_alert(
                                    model_id, ratio, llm_conf_root
                                )
                                ratio_alert_recorded = True
                    except Exception:  # noqa: BLE001
                        pass
                    last_activity = now
                else:
                    last_activity = now
            # --- finalize ---
            # Edge case: abort signalled after provider exhausted but before
            # finalize section executes (race where abort arrives between
            # last yield and finalize). Convert to aborted path.
            if abort_registry.is_aborted(request_id):
                if abort_started_at is None:
                    abort_started_at = (
                        abort_registry.abort_started_at(request_id)
                        or time.time()
                    )
                raise RuntimeError("aborted")
            now = time.time()
            latency_ms = int((now - t_start) * 1000)
            if reasoning_stats and reasoning_final_detect_ts:
                buffering_ms = int(
                    (now - reasoning_final_detect_ts) * 1000
                )
                try:
                    metrics.observe(
                        "reasoning_buffer_latency_ms",
                        buffering_ms,
                        {"model": model_id},
                    )
                except Exception:  # noqa: BLE001
                    pass
            final_text = "".join(fragments)
            if not minimal_mode:
                final_text = _strip_echo(
                    base_sp_effective, req.prompt, final_text
                )
            if stop_hit and final_text.endswith(stop_hit):
                final_text = final_text[: -len(stop_hit)]
            # Populate ctx
            ctx.fragments = fragments
            ctx.reasoning_stats = reasoning_stats or (
                {
                    "reasoning_tokens": 0,
                    "final_tokens": tokens_out,
                    "reasoning_ratio": 0.0,
                }
                if effective_reasoning_mode
                else None
            )
            if (
                ctx.reasoning_stats
                and "final_tokens" not in ctx.reasoning_stats
            ):
                ctx.reasoning_stats["final_tokens"] = tokens_out
            ctx.stop_hit = stop_hit
            ctx.output_tokens = tokens_out
            ctx.latency_ms = latency_ms
            decode_tps = (
                (tokens_out / (latency_ms / 1000.0))
                if tokens_out and latency_ms
                else 0.0
            )
            ctx.decode_tps = decode_tps
            res = pipeline.finalize(ctx)
            prev_gpu_layers_effective = gpu_layers_effective
            prev_gpu_layers_requested = gpu_layers_requested
            try:
                if callable(getter_effective):
                    gpu_layers_effective = getter_effective()
            except Exception:  # noqa: BLE001
                pass
            try:
                if callable(getter_requested):
                    gpu_layers_requested = getter_requested()
            except Exception:  # noqa: BLE001
                pass
            if (
                gpu_layers_requested is None
                and requested_gpu_layers_override is not None
            ):
                gpu_layers_requested = requested_gpu_layers_override
            gpu_offload = bool(
                gpu_layers_effective is not None
                and gpu_layers_effective > 0
            )
            gpu_layers_fallback = bool(
                gpu_layers_effective in (None, 0)
                and gpu_layers_requested not in (None, "auto", 0)
            )
            change_label = None
            if prev_gpu_layers_effective != gpu_layers_effective and (
                prev_gpu_layers_requested != gpu_layers_requested
            ):
                change_label = "both"
            elif prev_gpu_layers_effective != gpu_layers_effective:
                change_label = "effective"
            elif prev_gpu_layers_requested != gpu_layers_requested:
                change_label = "requested"
            if change_label:
                try:
                    metrics.inc(
                        "gpu_layer_state_sync_total",
                        {
                            "change": change_label,
                            "model": model_id,
                        },
                    )
                except Exception:  # noqa: BLE001
                    pass
            try:
                metrics.inc(
                    "gpu_offload_state_total",
                    {
                        "model": model_id,
                        "offload": "1" if gpu_offload else "0",
                    },
                )
            except Exception:  # noqa: BLE001
                pass
            if gpu_layers_fallback and not fallback_warning_emitted:
                fallback_payload = {
                    "event": "GpuFallback",
                    "request_id": request_id,
                    "model_id": model_id,
                    "requested": gpu_layers_requested,
                    "effective": gpu_layers_effective,
                }
                try:
                    yield format_event("warning", json.dumps(fallback_payload))
                    fallback_warning_emitted = True
                except Exception:  # noqa: BLE001
                    pass
            metrics.observe(
                "generation_latency_ms", latency_ms, {"model": model_id}
            )
            metrics.observe(
                "generation_decode_tps", decode_tps, {"model": model_id}
            )
            # SSE usage strictly from pipeline result (single source)
            usage_payload = {
                "request_id": request_id,
                "model_id": model_id,
                **(res.usage or {}),
            }
            if first_token_latency_ms is not None:
                usage_payload["first_token_latency_ms"] = int(
                    first_token_latency_ms
                )
            if gpu_layers_effective is not None:
                usage_payload["n_gpu_layers"] = gpu_layers_effective
                usage_payload["gpu_offload"] = gpu_offload
            if gpu_layers_requested is not None:
                usage_payload["requested_n_gpu_layers"] = (
                    gpu_layers_requested
                )
            if gpu_layers_fallback:
                usage_payload["gpu_fallback"] = True
            # Include sampling cap flags for UI from sampling_summary
            try:
                ss = res.sampling_summary or {}
                if ss:
                    if "cap_applied" in ss:
                        usage_payload["cap_applied"] = bool(
                            ss.get("cap_applied")
                        )
                    if "effective_max_tokens" in ss:
                        usage_payload["effective_max_tokens"] = (
                            ss.get("effective_max_tokens")
                        )
                    else:
                        if "effective_max_tokens" not in usage_payload:
                            # ctx fallback (should be redundant)
                            usage_payload["effective_max_tokens"] = (
                                effective_max_tokens
                            )
            except Exception:  # noqa: BLE001
                # fallback to ctx-derived tokens already set above if needed
                pass
            yield format_event("usage", json.dumps(usage_payload))
            if reasoning_text:
                yield format_event(
                    "reasoning",
                    json.dumps(
                        {
                            "request_id": request_id,
                            "model_id": model_id,
                            "reasoning_text": reasoning_text,
                            "stats": ctx.reasoning_stats,
                        }
                    ),
                )
            # prefer pipeline's final_text (echo-stripped)
            final_text = res.final_text or final_text
            if final_text:
                try:
                    store.add(session_id, "assistant", final_text)
                except Exception:  # noqa: BLE001
                    pass
            final_payload = {
                "request_id": request_id,
                "model_id": model_id,
                "text": final_text,
                "reasoning_text": None,
                "stop_reason": stop_hit and "stop_sequence" or None,
                "stats": ctx.reasoning_stats,
                "cap_applied": bool(cap_applied),
                "effective_max_tokens": effective_max_tokens,
            }
            if gpu_layers_effective is not None:
                final_payload["n_gpu_layers"] = gpu_layers_effective
                final_payload["gpu_offload"] = gpu_offload
            if gpu_layers_requested is not None:
                final_payload["requested_n_gpu_layers"] = (
                    gpu_layers_requested
                )
            if gpu_layers_fallback:
                final_payload["gpu_fallback"] = True
            if first_token_latency_ms is not None:
                final_payload["first_token_latency_ms"] = int(
                    first_token_latency_ms
                )
            yield format_event("final", json.dumps(final_payload))
            # Fallback: if abort arrived late (after finalize path already
            # underway) still record cancel latency metric so tests &
            # observability capture user intent. Treat as user_abort path.
            # Consider both the boolean aborted flag and the presence of an
            # abort start timestamp (mark_start) to catch cases where the
            # generation finished before abort() was called but intent was
            # recorded. Emit before 'end' so observers can see the event.
            if is_test_mode:
                print(
                    "DEBUG_LATE_ABORT_CHECK",
                    request_id,
                    abort_registry.is_aborted(request_id),
                    abort_started_at,
                    abort_registry.abort_started_at(request_id),
                )
            if (
                abort_registry.is_aborted(request_id)
                or abort_started_at is not None
                or abort_registry.abort_started_at(request_id) is not None
            ):
                try:
                    _src = (
                        abort_started_at
                        or abort_registry.abort_started_at(request_id)
                        or t_start
                    )
                    _dur_ms = int((time.time() - _src) * 1000)
                    metrics.observe(
                        "cancel_latency_ms", _dur_ms, {"path": "user_abort"}
                    )
                    metrics.inc(
                        "cancel_latency_events_total",
                        {"path": "user_abort"},
                    )
                    # Emit GenerationCancelled as a late-abort marker
                    try:
                        if is_test_mode:
                            print(
                                "DEBUG_EMIT_GEN_CANCEL",
                                request_id,
                                "phase",
                                "late-success",
                            )
                        emit(
                            GenerationCancelled(
                                request_id=request_id,
                                model_id=model_id,
                                role=provider.info().role,
                                reason="user_abort",
                                latency_ms=latency_ms,
                                output_tokens=tokens_out,
                                correlation_id=request_id,
                                message="aborted-late",
                            )
                        )
                        try:
                            metrics.inc(
                                "generation_cancelled_total",
                                {"model": model_id, "reason": "user_abort"},
                            )
                        except Exception:  # noqa: BLE001
                            pass
                    except Exception:  # noqa: BLE001
                        pass
                    try:
                        emit(
                            CancelLatencyMeasured(
                                request_id=request_id,
                                model_id=model_id,
                                duration_ms=_dur_ms,
                                path="user_abort",
                            )
                        )
                    except Exception:  # noqa: BLE001
                        pass
                    cancel_latency_emitted = True
                except Exception:  # noqa: BLE001
                    pass
            yield format_event(
                "end",
                json.dumps({"request_id": request_id, "status": "ok"}),
            )
            metrics.inc(
                "sse_stream_close_total", {"model": model_id, "reason": "ok"}
            )
        except Exception as e:  # noqa: BLE001
            latency_ms = int((time.time() - t_start) * 1000)
            aborted = str(e) == "aborted"
            timeout = isinstance(e, TimeoutError) and str(e).startswith(
                "generation-timeout"
            )
            reason = "user_abort" if aborted else (
                "timeout" if timeout else "runtime-error"
            )
            if aborted or timeout:
                if is_test_mode:
                    print(
                        "DEBUG_EMIT_GEN_CANCEL",
                        request_id,
                        "phase",
                        "except-branch",
                        reason,
                    )
                emit(
                    GenerationCancelled(
                        request_id=request_id,
                        model_id=model_id,
                        role=provider.info().role,
                        reason=reason,
                        latency_ms=latency_ms,
                        output_tokens=tokens_out,
                        correlation_id=request_id,
                        message=(
                            "aborted-by-client" if aborted else str(e)
                        ),
                    )
                )
                generation_cancel_emitted = True
                try:
                    metrics.inc(
                        "generation_cancelled_total",
                        {"model": model_id, "reason": reason},
                    )
                except Exception:  # noqa: BLE001
                    pass
                # Cancel latency measurement (only user_abort)
                if aborted:
                    # Emit cancel latency immediately to ensure observability
                    # and set flag to avoid duplicate emission in finalizer.
                    try:
                        _src = (
                            abort_started_at
                            or abort_registry.abort_started_at(request_id)
                            or t_start
                        )
                        _dur_ms = int((time.time() - _src) * 1000)
                        try:
                            metrics.observe(
                                "cancel_latency_ms",
                                _dur_ms,
                                {"path": "user_abort"},
                            )
                            metrics.inc(
                                "cancel_latency_events_total",
                                {"path": "user_abort"},
                            )
                        except Exception:  # noqa: BLE001
                            pass
                        try:
                            emit(
                                CancelLatencyMeasured(
                                    request_id=request_id,
                                    model_id=model_id,
                                    duration_ms=_dur_ms,
                                    path="user_abort",
                                )
                            )
                        except Exception:  # noqa: BLE001
                            pass
                        cancel_latency_emitted = True
                    except Exception:  # noqa: BLE001
                        pass
            else:
                emit(
                    GenerationCompleted(
                        request_id=request_id,
                        model_id=model_id,
                        role=provider.info().role,
                        status="error",
                        correlation_id=request_id,
                        output_tokens=tokens_out,
                        latency_ms=latency_ms,
                        error_type="runtime-error",
                        message=str(e),
                        sampling_origin=sampling_origin,
                        merged_sampling=(
                            dict(base_kwargs) if base_kwargs else None
                        ),
                    )
                )
            err_payload = {
                "request_id": request_id,
                "model_id": model_id,
                "code": reason,
                "error_type": reason,
                "message": (
                    "aborted-by-client" if aborted else str(e)
                ),
            }
            if gpu_layers_effective is not None:
                err_payload["n_gpu_layers"] = gpu_layers_effective
                err_payload["gpu_offload"] = gpu_offload
            if gpu_layers_requested is not None:
                err_payload["requested_n_gpu_layers"] = (
                    gpu_layers_requested
                )
            if gpu_layers_fallback:
                err_payload["gpu_fallback"] = True
            if tokens_out and fragments:
                try:
                    store.add(session_id, "assistant", "".join(fragments))
                except Exception:  # noqa: BLE001
                    pass
            try:
                decode_tps = (
                    (tokens_out / (time.time() - t_start))
                    if tokens_out
                    else 0.0
                )
                usage_payload = {
                    "request_id": request_id,
                    "model_id": model_id,
                    "prompt_tokens": prompt_tokens,
                    "output_tokens": tokens_out,
                    "latency_ms": latency_ms,
                    "decode_tps": decode_tps,
                }
                if gpu_layers_effective is not None:
                    usage_payload["n_gpu_layers"] = gpu_layers_effective
                    usage_payload["gpu_offload"] = gpu_offload
                if gpu_layers_requested is not None:
                    usage_payload["requested_n_gpu_layers"] = (
                        gpu_layers_requested
                    )
                if gpu_layers_fallback:
                    usage_payload["gpu_fallback"] = True
                yield format_event("usage", json.dumps(usage_payload))
            except Exception:  # noqa: BLE001
                pass
            yield format_event("error", json.dumps(err_payload))
            yield format_event(
                "end",
                json.dumps(
                    {
                        "request_id": request_id,
                        "status": (
                            "cancelled" if aborted or timeout else "error"
                        ),
                        "error_type": err_payload["error_type"],
                    }
                ),
            )
            metrics.inc(
                "sse_stream_close_total",
                {
                    "model": model_id,
                    "reason": err_payload["error_type"],
                },
            )
        finally:
            # Centralized cancel latency emission (single source of truth)
            try:
                if (
                    abort_registry.is_aborted(request_id)
                    and not cancel_latency_emitted
                ):
                    duration_source = (
                        abort_started_at
                        or abort_registry.abort_started_at(request_id)
                    )
                    if duration_source is not None:
                        dur_ms = int((time.time() - duration_source) * 1000)
                        try:
                            metrics.observe(
                                "cancel_latency_ms",
                                dur_ms,
                                {"path": "user_abort"},
                            )
                            metrics.inc(
                                "cancel_latency_events_total",
                                {"path": "user_abort"},
                            )
                        except Exception:  # noqa: BLE001
                            pass
                        try:
                            emit(
                                CancelLatencyMeasured(
                                    request_id=request_id,
                                    model_id=model_id,
                                    duration_ms=dur_ms,
                                    path="user_abort",
                                )
                            )
                        except Exception:  # noqa: BLE001
                            pass
                        cancel_latency_emitted = True
                # Ensure GenerationCancelled is emitted at least once if an
                # abort intent was recorded (mark_start) even if the stream
                # completed before abort() took effect (late abort race).
                if (
                    (
                        abort_started_at is not None
                        or (
                            abort_registry.abort_started_at(request_id)
                            is not None
                        )
                    )
                    and not generation_cancel_emitted
                ):
                    try:
                        if is_test_mode:
                            print(
                                "DEBUG_EMIT_GEN_CANCEL",
                                request_id,
                                "phase",
                                "finalizer",
                            )
                        emit(
                            GenerationCancelled(
                                request_id=request_id,
                                model_id=model_id,
                                role=provider.info().role,
                                reason="user_abort",
                                latency_ms=int((time.time() - t_start) * 1000),
                                output_tokens=tokens_out,
                                correlation_id=request_id,
                                message="aborted-late-finalizer",
                            )
                        )
                        generation_cancel_emitted = True
                        try:
                            metrics.inc(
                                "generation_cancelled_total",
                                {"model": model_id, "reason": "user_abort"},
                            )
                        except Exception:  # noqa: BLE001
                            pass
                    except Exception:  # noqa: BLE001
                        pass
            finally:  # ensure abort registry cleared even on metric failure
                def _deferred():
                    try:
                        # Late-arriving abort intent: emit markers if missed
                        start_ts = abort_registry.abort_started_at(
                            request_id
                        )
                        if start_ts is not None:
                            try:
                                # Cancel latency
                                dur_ms = int(
                                    (time.time() - start_ts) * 1000
                                )
                                emit(
                                    CancelLatencyMeasured(
                                        request_id=request_id,
                                        model_id=model_id,
                                        duration_ms=dur_ms,
                                        path="user_abort",
                                    )
                                )
                            except Exception:
                                pass
                            try:
                                emit(
                                    GenerationCancelled(
                                        request_id=request_id,
                                        model_id=model_id,
                                        role=provider.info().role,
                                        reason="user_abort",
                                        latency_ms=int(
                                            (time.time() - t_start) * 1000
                                        ),
                                        output_tokens=tokens_out,
                                        correlation_id=request_id,
                                        message="aborted-late-timer",
                                    )
                                )
                            except Exception:
                                pass
                    finally:
                        abort_registry.clear(request_id)

                # Delay a bit to catch mark_start() after stream end
                threading.Timer(0.2, _deferred).start()

    try:
        mismatch_events: list[ModelPassportMismatch] = []

        def _capture(ev):  # noqa: D401
            if isinstance(ev, ModelPassportMismatch) and getattr(
                ev, "model_id", None
            ) == model_id:
                mismatch_events.append(ev)

        _unsub = subscribe(_capture)

        def _gen_with_warnings():
            emitted_warnings = False
            inner = _iter()
            for item in inner:
                if not emitted_warnings and mismatch_events:
                    for ev in mismatch_events:
                        payload = {
                            "event": "ModelPassportMismatch",
                            "request_id": request_id,
                            "model_id": ev.model_id,
                            "field": ev.field,
                            "passport_value": ev.passport_value,
                            "config_value": ev.config_value,
                        }
                        yield format_event("warning", json.dumps(payload))
                    emitted_warnings = True
                yield item
            if not mismatch_events:
                return
            if not emitted_warnings:
                for ev in mismatch_events:
                    payload = {
                        "event": "ModelPassportMismatch",
                        "request_id": request_id,
                        "model_id": ev.model_id,
                        "field": ev.field,
                        "passport_value": ev.passport_value,
                        "config_value": ev.config_value,
                    }
                    yield format_event("warning", json.dumps(payload))

        return StreamingResponse(
            _gen_with_warnings(), media_type="text/event-stream"
        )
    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc()
        err_payload = {
            "error_type": "stream-init",
            "message": str(e),
            "phase": "pre_stream",
            "model_id": model_id,
            "request_id": request_id,
        }
        print("STREAM_INIT_ERROR", json.dumps(err_payload), "TRACE", tb)
        raise HTTPException(status_code=500, detail=err_payload) from e
    finally:
        try:  # unsubscribe if defined
            _unsub()  # type: ignore[name-defined]
        except Exception:  # noqa: BLE001
            pass


__all__ = ["router"]
