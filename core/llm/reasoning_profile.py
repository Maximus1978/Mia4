"""Reasoning profile resolver (per-model reasoning_levels).

Loads reasoning_levels from model passport (metadata already attached in
provider.info().metadata) and merges with user overrides applying safety
clamps and percent-based max token derivation.

Merge order:
  passport.sampling_defaults -> level overrides -> user overrides -> clamps
"""
from __future__ import annotations

from typing import Any, Tuple


def resolve_reasoning_profile(
    model_meta: dict | None,
    level: str | None,
    user_overrides: dict[str, Any] | None = None,
) -> Tuple[dict[str, Any], dict[str, Any]]:
    """Return (sampling_kwargs, reasoning_info).

    reasoning_info keys:
      level, reasoning_max_tokens, effective_max_output_tokens,
      origin_chain(list), clamps(list[str])
    """
    user_overrides = user_overrides or {}
    meta = model_meta or {}
    sampling_defaults = meta.get("passport_sampling_defaults", {}) or {}
    levels = meta.get("reasoning_levels") or {}
    base_max = int(
        sampling_defaults.get("max_output_tokens")
        or sampling_defaults.get("max_tokens")
        or 1024
    )

    origin: list[str] = []
    sampling: dict[str, Any] = {}

    # 1. passport defaults
    for k, v in sampling_defaults.items():
        if v is not None:
            sampling[k] = v
    if sampling:
        origin.append("passport")

    if not level:
        # no reasoning level requested
        info = {
            "level": None,
            "reasoning_max_tokens": 0,
            "effective_max_output_tokens": (
                sampling.get("max_output_tokens")
                or sampling.get("max_tokens")
                or base_max
            ),
            "origin_chain": origin,
            "clamps": [],
        }
        return sampling, info

    lvl = levels.get(level)
    if lvl:
        origin.append("level")
        # temperature / top_p etc.
        for key in ("temperature", "top_p", "top_k"):
            if key in lvl and lvl[key] is not None:
                sampling[key] = lvl[key]
        pct = lvl.get("max_output_tokens_pct")
        if pct is not None:
            try:
                pct_f = float(pct)
            except Exception:  # noqa: BLE001
                pct_f = 1.0
        else:
            pct_f = 1.0
        pct_f = max(0.05, min(pct_f, 0.9))
        eff_final_max = int(base_max * pct_f)
        sampling["max_output_tokens"] = eff_final_max
        reasoning_cap = int(lvl.get("reasoning_max_tokens", 0) or 0)
    else:
        # fallback old presets path (leave to caller) – treat as no level
        reasoning_cap = 0
        eff_final_max = int(sampling.get("max_output_tokens") or base_max)

    # 2. user overrides
    if user_overrides:
        origin.append("user")
        if "max_tokens" in user_overrides:
            sampling["max_output_tokens"] = user_overrides["max_tokens"]
        for k, v in user_overrides.items():
            if k in {
                "temperature",
                "top_p",
                "top_k",
                "repeat_penalty",
                "presence_penalty",
                "frequency_penalty",
            }:
                sampling[k] = v

    clamps: list[str] = []
    # Derive post user override effective max
    eff_final_max = int(
        sampling.get("max_output_tokens")
        or sampling.get("max_tokens")
        or eff_final_max
    )

    # Safety clamp: reasoning_cap <= 0.5 * final
    if reasoning_cap > int(eff_final_max * 0.5):
        reasoning_cap = int(eff_final_max * 0.5)
        clamps.append("ratio")

    sampling_info = {
        "level": level,
        "reasoning_max_tokens": reasoning_cap,
        "effective_max_output_tokens": eff_final_max,
        "origin_chain": origin,
        "clamps": clamps,
    }
    return sampling, sampling_info


__all__ = ["resolve_reasoning_profile"]
