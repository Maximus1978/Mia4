"""High-level agent operations (judge, plan) emitting structured events.

These are placeholder implementations that:
  - Apply reasoning mode overrides
  - Invoke underlying model provider via factory routing
  - Emit JudgeInvocation / PlanGenerated events

They allow tests to validate event flow without full agent loop.
"""
from __future__ import annotations

from typing import Dict, Any, List
import uuid

from core.events import (
    emit,
    JudgeInvocation,
    PlanGenerated,
    ReasoningPresetApplied,
)
from .factory import get_model_by_role, apply_reasoning_overrides, sweep_idle
from core.config.loader import get_config


def judge(
    target_request_id: str,
    prompt: str,
    reasoning_mode: str = "low",
    repo_root: str = ".",
) -> Dict[str, Any]:
    req_id = uuid.uuid4().hex
    provider = get_model_by_role("judge", repo_root=repo_root)
    gen_kwargs = apply_reasoning_overrides({}, reasoning_mode)
    # Emit reasoning preset selection event
    if reasoning_mode:
        emit(
            ReasoningPresetApplied(
                request_id=req_id,
                mode=reasoning_mode,
                temperature=gen_kwargs.get("temperature"),
                top_p=gen_kwargs.get("top_p"),
            )
        )
    gen = provider.generate(prompt, **gen_kwargs, max_tokens=64)
    # provider.generate now returns GenerationResult
    text = gen.text if hasattr(gen, "text") else str(gen)
    agreement = min(1.0, max(0.0, len(text.split()) / 64))
    emit(
        JudgeInvocation(
            request_id=req_id,
            model_id=provider.info().id,
            target_request_id=target_request_id,
            agreement=agreement,
        )
    )
    # Idle sweep (lightweight): build idle map from optional models config
    idle_conf = {}
    opt = get_config().llm.optional_models
    for mid, spec in opt.items():
        if spec.enabled:
            idle_conf[spec.id] = spec.idle_unload_seconds
    sweep_idle(idle_conf)
    return {"request_id": req_id, "text": text, "agreement": agreement}


def plan(
    objective: str,
    max_steps: int = 8,
    reasoning_mode: str = "medium",
    repo_root: str = ".",
) -> Dict[str, Any]:
    req_id = uuid.uuid4().hex
    provider = get_model_by_role("planner", repo_root=repo_root)
    gen_kwargs = apply_reasoning_overrides({}, reasoning_mode)
    prompt = f"Outline up to {max_steps} high-level steps to: {objective}"  # noqa: E501
    if reasoning_mode:
        emit(
            ReasoningPresetApplied(
                request_id=req_id,
                mode=reasoning_mode,
                temperature=gen_kwargs.get("temperature"),
                top_p=gen_kwargs.get("top_p"),
            )
        )
    gen = provider.generate(prompt, **gen_kwargs, max_tokens=128)
    raw = gen.text if hasattr(gen, "text") else str(gen)
    lines = [line.strip(" -") for line in raw.splitlines() if line.strip()]
    steps: List[str] = []
    for line in lines:
        if len(steps) >= max_steps:
            break
        if len(line.split()) >= 2:
            steps.append(line)
    if not steps:
        steps = [objective]
    emit(
        PlanGenerated(
            request_id=req_id,
            steps_count=len(steps),
            model_id=provider.info().id,
        )
    )
    idle_conf = {}
    opt = get_config().llm.optional_models
    for mid, spec in opt.items():
        if spec.enabled:
            idle_conf[spec.id] = spec.idle_unload_seconds
    sweep_idle(idle_conf)
    return {"request_id": req_id, "steps": steps, "raw": raw}


__all__ = ["judge", "plan"]
