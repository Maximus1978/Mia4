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
    top_k: int = 40
    repeat_penalty: float = 1.1
    min_p: float = 0.05
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

    @field_validator("top_k")
    @classmethod
    def _top_k_range(cls, v: int) -> int:  # noqa: D401
        if v <= 0:
            raise ValueError("top_k must be >0")
        return v

    @field_validator("repeat_penalty")
    @classmethod
    def _repeat_penalty_range(cls, v: float) -> float:  # noqa: D401
        if not (0.5 <= v <= 2.5):
            raise ValueError("repeat_penalty out of range 0.5..2.5")
        return v

    @field_validator("min_p")
    @classmethod
    def _min_p_range(cls, v: float) -> float:  # noqa: D401
        if not (0.0 <= v <= 1.0):
            raise ValueError("min_p out of range 0..1")
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
    lightweight: LightweightLLMConfig | None = Field(
        default_factory=lambda: LightweightLLMConfig(
            id="phi-3.5-mini-instruct-q3_k_s", temperature=0.4
        )
    )
    optional_models: Dict[str, OptionalMoEConfig] = Field(default_factory=dict)
    # Threshold (GB) above which a model is considered "heavy" and triggers
    # auto-unload of previously loaded heavy models on switch.
    heavy_model_vram_threshold_gb: float = 10.0
    skip_checksum: bool = False
    load_timeout_ms: int = 15000
    # Generation timeout (server-side streaming hard stop)
    generation_timeout_s: int = 120
    # Additional grace period before first token (covers model warm-up)
    generation_initial_idle_grace_s: int = 45
    # Reasoning presets: mode -> overrides for generation params
    reasoning_presets: Dict[str, Dict[str, float | int]] = Field(
        default_factory=lambda: {
            # Provide baseline reasoning_max_tokens so tests that access it
            # without full base.yaml (isolated config) still pass.
            "low": {
                "temperature": 0.6,
                "top_p": 0.9,
                "reasoning_max_tokens": 128,
            },
            "medium": {
                "temperature": 0.7,
                "top_p": 0.92,
                "reasoning_max_tokens": 256,
            },
            "high": {
                "temperature": 0.85,
                "top_p": 0.95,
                "reasoning_max_tokens": 512,
            },
        }
    )
    # Base system prompt (Layer 1) configuration (Phase 3 backlog enablement)
    system_prompt: Dict[str, object] = Field(
        default_factory=lambda: {
            "version": 1,
            "allow_user_override": False,
            "max_persona_chars": 1200,
            # Provide non-empty default text so tests that assert presence
            # pass even if base.yaml override missing in isolated test env.
            "text": "[SYSTEM]\nBase prompt not configured."
        }
    )
    # Post-processing (reasoning split + ngram suppression)
    postproc: Dict[str, object] = Field(
        default_factory=lambda: {
            "enabled": True,
            "reasoning": {
                "max_tokens": 256,
                "drop_from_history": True,
                "ratio_alert_threshold": 0.45,
            },
            "ngram": {"n": 3, "window": 128},
            "collapse": {"whitespace": True},
        }
    )
    # Harmony prompt (Phase 3) feature flag & tags
    prompt: Dict[str, object] = Field(
        default_factory=lambda: {
            "harmony": {
                "enabled": True,
                "force": True,
                "tags": {"analysis": "analysis", "final": "final"},
            }
        }
    )
    # Commentary retention policy (ADR-0024) - minimal stub (metrics_only)
    commentary_retention: Dict[str, object] = Field(
        default_factory=lambda: {
            # mode values:
            #   metrics_only | hashed_slice | redacted_snippets | raw_ephemeral
            "mode": "metrics_only",
            "hashed_slice": {"max_chars": 160},
            "redacted_snippets": {
                "max_tokens": 40,
                "redact_pattern": "(?i)(user|secret|api[_-]?key)",
                "replacement": "***",
            },
            "raw_ephemeral": {"ttl_seconds": 300},
            "store_to_history": False,
            # tool_chain override sub-block (detect + override policy)
            "tool_chain": {
                "detect": True,
                # apply_when: raw_ephemeral|hashed_slice|redacted_snippets|any
                "apply_when": "raw_ephemeral",
                # override_mode: hashed_slice|redacted_snippets
                "override_mode": "hashed_slice",
                "tag_in_summary": True,
            },
        }
    )
    # Tool calling feature (MVP) configuration
    tool_calling: Dict[str, object] = Field(
        default_factory=lambda: {
            "enabled": True,
            "max_payload_bytes": 8192,
            "retention": {
                "mode": "hashed_slice",
                "hash_preview_max_chars": 120,
                "redacted_placeholder": "[REDACTED]",
            },
        }
    )
    # Global stop sequences (legacy compatibility; empty by default)
    stop: list[str] = Field(default_factory=list)
    # Dev/test fake provider toggle (legacy compatibility)
    fake: bool = False

    model_config = ConfigDict(extra="forbid")
