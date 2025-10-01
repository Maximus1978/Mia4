"""Primary model generation pipeline implementation (phase 1 extraction).

Currently focuses on prepare() responsibilities only; streaming & finalize
logic remain inside the route until subsequent refactor steps.
"""
from __future__ import annotations

from typing import Any
import hashlib
import datetime as _dt

from core.config import get_config
from core import metrics
from core.events import (
    GenerationStarted,
    GenerationCompleted,
    emit,
    ModelRouted,
    ModelPassportMismatch,
    GenerationCancelled,
)
from core.llm.adapters import HarmonyChannelAdapter
from .base import (
    PipelineContext,
    PipelineSampling,
    GenerationPipeline,
    PipelineResult,
)


class PrimaryPipeline(GenerationPipeline):  # pragma: no cover
    def _approx_tokens(self, text: str) -> int:
        try:
            return max(1, len((text or "").split()))
        except Exception:
            return max(1, len(text) // 4)

    def _build_harmony_prompt(
        self,
        *,
        system_prompt_text: str,
        dev_block_text: str,
        reasoning_mode: str | None,
        session_messages: list[tuple[str, str]] | None,
        user_prompt: str,
        context_length: int | None,
        reserved_output_tokens: int | None,
    ) -> tuple[str, int, str | None]:  # noqa: D401
        lvl = (reasoning_mode or "medium").lower()
        now = _dt.datetime.utcnow().strftime("%Y-%m-%d")
        system_lines = [
            "You are ChatGPT, a large language model trained by OpenAI.",
            "Knowledge cutoff: 2024-10",
            f"Current date: {now}",
            f"Reasoning: {lvl}",
            (
                "# Valid channels: analysis, commentary, final. "
                "Channel must be included for every message."
            ),
        ]
        system_msg = "\n".join(system_lines)
        dev_block = dev_block_text
        if not dev_block.startswith("# Instructions"):
            dev_block = "# Instructions\n" + dev_block.strip()
    # Build history with a simple character budget heuristic
    # (~4 chars/token)
        chars_per_token = 4
        budget_tokens = None
        try:
            if context_length:
                budget_tokens = max(
                    128,
                    int(context_length) - int(reserved_output_tokens or 256),
                )
        except Exception:
            budget_tokens = None
        budget_chars = (
            budget_tokens * chars_per_token if budget_tokens else None
        )
        parts: list[str] = []
        parts.append("<|start|>system<|message|>" + system_msg + "<|end|>")
        parts.append(
            "<|start|>developer<|message|>" + dev_block + "<|end|>"
        )
    # Append prior history (excluding final assistant tag)
    # oldest -> newest
        history = session_messages or []
    # Ensure last message is current user prompt if history provided
        # We'll reconstruct all but ensure we end with assistant tag open
        for role, content in history:
            r = role.strip().lower()
            if r not in {"user", "assistant"}:
                continue
            tag = "user" if r == "user" else "assistant"
            parts.append(
                f"<|start|>{tag}<|message|>" + (content or "") + "<|end|>"
            )
        # Ensure the latest user prompt is present (in case history was empty)
        if (
            not history
            or history[-1][0] != "user"
            or history[-1][1] != user_prompt
        ):
            parts.append("<|start|>user<|message|>" + user_prompt + "<|end|>")
    # Assemble and clamp to budget if needed
    # (trim from the start of history)
        assembled = "".join(parts) + "<|start|>assistant"
        if budget_chars and len(assembled) > budget_chars:
            # Drop earliest history chunks (keep system+dev + latest turns)
            fixed = parts[:2]  # system + dev
            dyn = parts[2:]
            # Drop from the left until within budget
            for i in range(len(dyn)):
                candidate = "".join(fixed + dyn[i:]) + "<|start|>assistant"
                if len(candidate) <= budget_chars:
                    assembled = candidate
                    break
        prompt_tokens = self._approx_tokens(assembled)
        sp_hash = (
            hashlib.sha256(system_prompt_text.encode("utf-8")).hexdigest()[:16]
            if system_prompt_text
            else None
        )
        return assembled, prompt_tokens, sp_hash

    def prepare(
        self,
        *,
        request_id: str,
        model_id: str,
        provider: Any,
        prompt: str,
        session_messages: list[tuple[str, str]] | None = None,
        reasoning_mode: str | None,
        user_sampling: dict,
        passport_defaults: dict,
        sampling_origin: str | None,
    ) -> PipelineContext:  # noqa: D401
        base_kwargs = dict(user_sampling)
        cap_applied = False
        cap_source = None
        requested_max = base_kwargs.get("max_tokens")
        effective_max = requested_max
        try:  # Cap resolution
            passport_max = (
                passport_defaults.get("max_output_tokens")
                if passport_defaults
                else None
            )
            try:
                primary_cfg = get_config().llm.primary
                primary_limit = getattr(
                    primary_cfg, "max_output_tokens", None
                )
            except Exception:  # noqa: BLE001
                primary_limit = None
            # Emit mismatch warning if both present and differ
            if (
                isinstance(passport_max, (int, float))
                and isinstance(primary_limit, (int, float))
                and int(passport_max) != int(primary_limit)
            ):
                emit(
                    ModelPassportMismatch(
                        model_id=model_id,
                        field="max_output_tokens",
                        passport_value=int(passport_max),
                        config_value=int(primary_limit),
                    )
                )
            candidates = []
            for val, src in (
                (passport_max, "passport"),
                (primary_limit, "primary"),
            ):
                if isinstance(val, (int, float)) and val > 0:
                    candidates.append((int(val), src))
            if isinstance(requested_max, (int, float)) and candidates:
                candidates.sort(key=lambda x: x[0])
                for cval, src in candidates:
                    if requested_max > cval:
                        base_kwargs["max_tokens"] = cval
                        effective_max = cval
                        cap_applied = True
                        cap_source = src
                        metrics.inc(
                            "model_cap_hits_total",
                            {"model": model_id, "source": src},
                        )
                        break
        except Exception:  # noqa: BLE001
            pass
        if effective_max is None:
            effective_max = base_kwargs.get("max_tokens")
        # Tag custom sampling mode if user provided overrides
        if base_kwargs and any(
            k not in {"max_tokens"} for k in base_kwargs.keys()
        ):
            base_kwargs = {
                **base_kwargs,
                "mode": base_kwargs.get("mode", "custom"),
            }
        sampling_struct = PipelineSampling(
            requested_max_tokens=requested_max,
            effective_max_tokens=effective_max,
            cap_applied=cap_applied,
            cap_source=cap_source,
            merged=base_kwargs,
        )
        llm_cfg = get_config().llm
        base_sp = (
            getattr(llm_cfg.system_prompt, "text", "")
            if hasattr(llm_cfg, "system_prompt")
            else ""
        )
        dev_block = base_sp
        mi = provider.info()
        harmony_prompt, sp_version, sp_hash = self._build_harmony_prompt(
            system_prompt_text=base_sp,
            dev_block_text=dev_block,
            reasoning_mode=reasoning_mode,
            session_messages=session_messages,
            user_prompt=prompt,
            context_length=getattr(mi, "context_length", None),
            reserved_output_tokens=effective_max,
        )
        adapter = HarmonyChannelAdapter(getattr(llm_cfg, "postproc", {}))
        try:
            adapter.set_context(  # type: ignore[attr-defined]
                request_id=request_id,
                model_id=model_id,
            )
        except AttributeError:
            # Minimal fallback for legacy adapters without helper
            try:
                adapter.request_id = request_id  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass
            try:
                adapter.model_id = model_id  # type: ignore[attr-defined]
                adapter._model_id = model_id  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass
        ctx = PipelineContext(
            request_id=request_id,
            model_id=model_id,
            provider=provider,
            prompt=harmony_prompt,
            sampling=sampling_struct,
            adapter=adapter,
            adapter_name="harmony",
            prompt_tokens=self._approx_tokens(harmony_prompt),
            system_prompt_version=sp_version,
            system_prompt_hash=sp_hash,
            sampling_origin=sampling_origin,
            merged_sampling=base_kwargs,
            cap_applied=cap_applied,
            cap_source=cap_source,
            requested_max_tokens=requested_max,
            effective_max_tokens=effective_max,
            reasoning_mode=reasoning_mode,
            system_prompt_text=base_sp,
            user_prompt=prompt,
        )
    # Mirror sampling struct into convenience fields
    # if not already consistent
        if ctx.cap_applied is None:
            ctx.cap_applied = sampling_struct.cap_applied
        if ctx.effective_max_tokens is None:
            ctx.effective_max_tokens = sampling_struct.effective_max_tokens
        emit(
            ModelRouted(
                request_id=request_id,
                model_id=model_id,
                pipeline="primary",
                capabilities={
                    "reasoning_split": True,
                    "tool_calls": True,
                },
            )
        )
        emit(
            GenerationStarted(
                request_id=request_id,
                model_id=model_id,
                role=provider.info().role,
                prompt_tokens=ctx.prompt_tokens,
                system_prompt_version=sp_version,
                system_prompt_hash=sp_hash,
                persona_len=0,
                sampling_origin=sampling_origin,
                merged_sampling=base_kwargs,
                sampling={
                    "requested_max_tokens": requested_max,
                    "effective_max_tokens": effective_max,
                    "cap_applied": cap_applied,
                    "cap_source": cap_source,
                    **(
                        {"max_tokens": base_kwargs.get("max_tokens")}
                        if base_kwargs.get("max_tokens")
                        else {}
                    ),
                },
                stop_sequences=None,
                cap_applied=cap_applied,
            )
        )
        return ctx

    def stream(self, ctx: PipelineContext):  # noqa: D401
        provider = ctx.provider
        adapter = ctx.adapter
    # If provider is a stub (internal llama stub or our
    # deterministic stub), wrap its raw token stream into a
    # Harmony final channel so the adapter emits token events
    # for SSE API.
        try:
            is_internal_stub = getattr(
                getattr(provider, "_state", None), "stub", False
            )
            meta = {}
            try:
                info_meta = getattr(provider.info(), "metadata", None)
                if isinstance(info_meta, dict):
                    meta = info_meta
            except Exception:  # noqa: BLE001
                pass
            is_stub_provider = bool(meta.get("stub")) or (
                getattr(provider.__class__, "__name__", "")
                == "_StubProvider"
            )
            if is_internal_stub or is_stub_provider:
                from mia4.api import abort_registry  # local import
                # Open final channel
                for ev in adapter.process_chunk(
                    "<|start|>assistant<|channel|>final<|message|>"
                ):
                    yield ev
                # Pipe raw tokens through adapter as content
                raw_stream = provider.stream(
                    ctx.prompt, **(ctx.merged_sampling or {})
                )
                for chunk in raw_stream:
                    if abort_registry.is_aborted(ctx.request_id):
                        raise RuntimeError("aborted")
                    for ev in adapter.process_chunk(chunk):
                        yield ev
                # Close channel
                for ev in adapter.process_chunk("<|return|>"):
                    yield ev
                for ev in adapter.finalize():  # type: ignore[attr-defined]
                    yield ev
                return
        except Exception:  # noqa: BLE001
            pass
        raw_stream = provider.stream(ctx.prompt, **(ctx.merged_sampling or {}))
        # Simple passthrough loop; adapter already harmony
        from mia4.api import abort_registry  # local import to avoid cycles
        for chunk in raw_stream:
            # Abort fast-path (checked per provider chunk)
            if abort_registry.is_aborted(ctx.request_id):
                raise RuntimeError("aborted")
            for ev in adapter.process_chunk(  # type: ignore[attr-defined]
                chunk
            ):
                yield ev
            # SSOT: never emit raw fallback fragments; wait for structured
            # channel events to avoid leaking Harmony service markers.
        for ev in adapter.finalize():  # type: ignore[attr-defined]
            yield ev

    def finalize(self, ctx: PipelineContext):  # noqa: D401
        # Heuristic echo-strip to avoid showing system/user echoes
        def _strip_echo(sp: str | None, up: str | None, text: str) -> str:
            if not text:
                return text
            sp_norm = (sp or "").strip()
            up_norm = (up or "").strip()
            out = text
            for _ in range(2):
                if sp_norm and out.lower().startswith(sp_norm.lower()[:120]):
                    out = out[len(sp_norm):].lstrip()
                else:
                    break
            for _ in range(2):
                if up_norm and out.lower().startswith(up_norm.lower()):
                    out = out[len(up_norm):].lstrip()
                else:
                    break
            cleaned_lines = []
            for ln in out.splitlines():
                lstrip = ln.strip()
                if not cleaned_lines and not lstrip:
                    continue
                if (
                    "[REASONING SPLIT]" in lstrip
                    or lstrip.startswith("[LEVEL]")
                ):
                    continue
                cleaned_lines.append(ln)
            return "\n".join(cleaned_lines).lstrip()

        # Prefer adapter-provided sanitized final text (SSOT) if present.
        if ctx.sanitized_final_text:
            final_text = ctx.sanitized_final_text
        else:
            joined = (
                ctx.fragments[0]
                if len(ctx.fragments) == 1
                else "".join(ctx.fragments)
            )
            final_text = _strip_echo(
                ctx.system_prompt_text,
                ctx.user_prompt,
                joined,
            )
        # Defensive duplicate collapse (backend should already sanitize).
        if final_text and len(final_text) % 2 == 0:
            half = len(final_text) // 2
            if half >= 16 and final_text[:half] == final_text[half:]:
                final_text = final_text[:half].rstrip()
        sampling_summary = {
            "requested_max_tokens": ctx.requested_max_tokens,
            "effective_max_tokens": ctx.effective_max_tokens,
            "cap_applied": bool(ctx.cap_applied),
            "cap_source": ctx.cap_source,
        }
        stop_reason = ctx.stop_hit and "stop_sequence" or None
        # Base usage
        usage = {
            "prompt_tokens": ctx.prompt_tokens,
            "output_tokens": ctx.output_tokens,
            "latency_ms": ctx.latency_ms,
            "decode_tps": ctx.decode_tps,
        }
    # Optional context usage (approx): prompt+output vs model
    # context_length
        try:
            _ctx_total = getattr(ctx.provider.info(), "context_length", None)
        except Exception:  # noqa: BLE001
            _ctx_total = None
        if _ctx_total:
            try:
                _used = (ctx.prompt_tokens or 0) + (ctx.output_tokens or 0)
                usage.update(
                    {
                        "context_used_tokens": _used,
                        "context_total_tokens": _ctx_total,
                        "context_used_pct": (
                            (_used / float(_ctx_total)) if _ctx_total else None
                        ),
                    }
                )
            except Exception:  # noqa: BLE001
                pass
        # Optional reasoning stats passthrough for SSE usage convenience
        if ctx.reasoning_stats:
            usage.update(
                {
                    "reasoning_tokens": ctx.reasoning_stats.get(
                        "reasoning_tokens"
                    ),
                    "final_tokens": ctx.reasoning_stats.get("final_tokens"),
                    "reasoning_ratio": ctx.reasoning_stats.get(
                        "reasoning_ratio"
                    ),
                }
            )
        usage = {k: v for k, v in usage.items() if v is not None}
        result_summary = {"sampling": sampling_summary}
        if ctx.reasoning_stats:
            result_summary["reasoning"] = {
                "reasoning_tokens": ctx.reasoning_stats.get(
                    "reasoning_tokens"
                ),
                "final_tokens": ctx.reasoning_stats.get("final_tokens"),
                "reasoning_ratio": ctx.reasoning_stats.get(
                    "reasoning_ratio"
                ),
                "adapter": ctx.adapter_name,
            }
        emit(
            GenerationCompleted(
                request_id=ctx.request_id,
                model_id=ctx.model_id,
                role=ctx.provider.info().role,
                status="ok",
                correlation_id=ctx.request_id,
                output_tokens=ctx.output_tokens,
                latency_ms=ctx.latency_ms or 0,
                result_summary=result_summary,
                stop_reason=stop_reason,
                sampling_origin=ctx.sampling_origin,
                merged_sampling=ctx.merged_sampling,
            )
        )
        # Backstop: if an abort intent was recorded, also emit a
        # GenerationCancelled marker so observers see the cancel even if
        # the route finalized successfully before abort took effect.
        try:
            from mia4.api import abort_registry as _ar  # noqa: WPS433
            if (
                _ar.abort_started_at(ctx.request_id) is not None
                or _ar.is_aborted(ctx.request_id)
            ):
                emit(
                    GenerationCancelled(
                        request_id=ctx.request_id,
                        model_id=ctx.model_id,
                        role=ctx.provider.info().role,
                        reason="user_abort",
                        latency_ms=ctx.latency_ms or 0,
                        output_tokens=ctx.output_tokens or 0,
                        correlation_id=ctx.request_id,
                        message="aborted-late-pipeline",
                    )
                )
        except Exception:
            pass
        return PipelineResult(
            final_text=final_text,
            usage=usage,
            reasoning_stats=ctx.reasoning_stats,
            sampling_summary=sampling_summary,
            stop_reason=stop_reason,
        )


__all__ = ["PrimaryPipeline"]

