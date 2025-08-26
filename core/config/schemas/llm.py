"""LLM config schema (modularized S1).

Extracted from legacy RootConfig.llm. This module intentionally contains
only LLM related structures. Optional model (MoE) settings remain nested.

No side effects / globals. Validation rules kept identical to legacy.
"""
from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, Field, field_validator, ConfigDict


class PrimaryLLMConfig(BaseModel):
    id: str
    temperature: float = 0.7
    top_p: float = 0.9
    max_output_tokens: int = 1024
    n_gpu_layers: str | int = "auto"
    # CPU tuning placeholders (threads and batch size)
    n_threads: int | None = None
    n_batch: int | None = None

    @field_validator("temperature")
    @classmethod
    def _temp_range(cls, v: float) -> float:  # noqa: D401
        if not (0 <= v <= 2):
            raise ValueError("temperature out of range 0..2")
        return v


class LightweightLLMConfig(BaseModel):
    id: str
    temperature: float = 0.4


class OptionalMoETimeouts(BaseModel):
    judge_ms: int = 4000
    plan_ms: int = 6000


class OptionalMoEConfig(BaseModel):
    enabled: bool = False
    id: str | None = None
    load_mode: str = Field("on_demand", pattern="^(on_demand|eager)$")
    idle_unload_seconds: int = 300
    reasoning_default: str = Field("low", pattern="^(low|medium|high)$")
    reasoning_overrides: Dict[str, str] = Field(default_factory=dict)
    timeouts: OptionalMoETimeouts = OptionalMoETimeouts()


class LLMConfig(BaseModel):
    primary: PrimaryLLMConfig
    lightweight: LightweightLLMConfig
    optional_models: Dict[str, OptionalMoEConfig] = Field(default_factory=dict)
    skip_checksum: bool = False
    load_timeout_ms: int = 15000
    # Reasoning presets: mode -> overrides for generation params
    reasoning_presets: Dict[str, Dict[str, float | int]] = Field(
        default_factory=lambda: {
            "low": {"temperature": 0.6, "top_p": 0.9},
            "medium": {"temperature": 0.7, "top_p": 0.92},
            "high": {"temperature": 0.85, "top_p": 0.95},
        }
    )

    model_config = ConfigDict(extra="forbid")
