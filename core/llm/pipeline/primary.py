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
    def _build_harmony_prompt(
        self,
        system_prompt: str,
        dev_block: str,
        user_prompt: str,
        reasoning_mode: str | None,
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
        if not dev_block.startswith("# Instructions"):
            dev_block = "# Instructions\n" + dev_block.strip()
        prompt = (
            "<|start|>system<|message|>" + system_msg + "<|end|>"
            + "<|start|>developer<|message|>" + dev_block + "<|end|>"
            + "<|start|>user<|message|>" + user_prompt + "<|end|>"
            + "<|start|>assistant"
        )
        return (
            prompt,
            1,
            (hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()[:16]
             if system_prompt else None),
        )

    def prepare(
        self,
        *,
        request_id: str,
        model_id: str,
        provider: Any,
        prompt: str,
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
        harmony_prompt, sp_version, sp_hash = self._build_harmony_prompt(
            base_sp, dev_block, prompt, reasoning_mode
        )
        adapter = HarmonyChannelAdapter(getattr(llm_cfg, "postproc", {}))
        ctx = PipelineContext(
            request_id=request_id,
            model_id=model_id,
            provider=provider,
            prompt=harmony_prompt,
            sampling=sampling_struct,
            adapter=adapter,
            adapter_name="harmony",
            prompt_tokens=len(harmony_prompt.split()),
            system_prompt_version=sp_version,
            system_prompt_hash=sp_hash,
            sampling_origin=sampling_origin,
            merged_sampling=base_kwargs,
            cap_applied=cap_applied,
            cap_source=cap_source,
            requested_max_tokens=requested_max,
            effective_max_tokens=effective_max,
            reasoning_mode=reasoning_mode,
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
        raw_stream = provider.stream(ctx.prompt, **(ctx.merged_sampling or {}))
        # Simple passthrough loop; adapter already harmony
        from mia4.api import abort_registry  # local import to avoid cycles
        for chunk in raw_stream:
            # Abort fast-path (checked per provider chunk)
            if abort_registry.is_aborted(ctx.request_id):
                raise RuntimeError("aborted")
            produced = False
            for ev in adapter.process_chunk(  # type: ignore[attr-defined]
                chunk
            ):
                produced = True
                yield ev
            # If adapter produced nothing (e.g., buffering), emit a
            # minimal delta
            if not produced:
                # Use a small slice to avoid large buffering side-effects
                text = str(chunk)[:16] if chunk is not None else ""
                if text:
                    yield {"type": "delta", "text": text}
        for ev in adapter.finalize():  # type: ignore[attr-defined]
            yield ev

    def finalize(self, ctx: PipelineContext):  # noqa: D401
        final_text = "".join(ctx.fragments)
        sampling_summary = {
            "requested_max_tokens": ctx.requested_max_tokens,
            "effective_max_tokens": ctx.effective_max_tokens,
            "cap_applied": bool(ctx.cap_applied),
            "cap_source": ctx.cap_source,
        }
        stop_reason = ctx.stop_hit and "stop_sequence" or None
        usage = {
            "prompt_tokens": ctx.prompt_tokens,
            "output_tokens": ctx.output_tokens,
            "latency_ms": ctx.latency_ms,
            "decode_tps": ctx.decode_tps,
        }
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
