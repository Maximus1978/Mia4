"""Configuration loading and validation.

Layer order (highest precedence last merge wins):
1. base.yaml
2. overrides.local.yaml (ignore if missing)
3. ENV (prefix MIA__ using double underscore to denote nesting)

Validation rules:
- Unknown keys rejected by pydantic model structure (implicit)
- Types validated via Pydantic models

Usage:
    from core.config.loader import get_config
    cfg = get_config()
    print(cfg.llm.primary.id)
"""
from __future__ import annotations

import os
import pathlib
import threading
from functools import lru_cache
from typing import Any, Dict

import yaml
from pydantic import BaseModel, Field, field_validator, ConfigDict

DEFAULT_CONFIG_DIR = "configs"
ENV_PREFIX = "MIA__"


class PrimaryLLMConfig(BaseModel):
    id: str
    temperature: float = 0.7
    top_p: float = 0.9
    max_output_tokens: int = 1024
    n_gpu_layers: str | int = "auto"
    # CPU tuning placeholders (Step 10.2): threads and batch size
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


class EmbeddingConfig(BaseModel):
    id: str


class EmbeddingsConfig(BaseModel):
    main: EmbeddingConfig
    fallback: EmbeddingConfig


class RAGHybridConfig(BaseModel):
    weight_semantic: float = 0.6
    weight_bm25: float = 0.4


class RAGNormalizeConfig(BaseModel):
    min_score: float = 0.0
    max_score: float = 1.0


class RAGConfig(BaseModel):
    collection_default: str = "memory"
    top_k: int = 8
    hybrid: RAGHybridConfig = RAGHybridConfig()
    normalize: RAGNormalizeConfig = RAGNormalizeConfig()


class EmotionFSMConfig(BaseModel):
    hysteresis_ms: int = 2000


class EmotionModelRef(BaseModel):
    id: str


class EmotionConfig(BaseModel):
    model: EmotionModelRef
    fsm: EmotionFSMConfig


class ReflectionSchedule(BaseModel):
    cron: str = "0 3 * * *"


class ReflectionConfig(BaseModel):
    enabled: bool = True
    schedule: ReflectionSchedule = ReflectionSchedule()


class MetricsExportConfig(BaseModel):
    prometheus_port: int = 9090


class MetricsConfig(BaseModel):
    export: MetricsExportConfig = MetricsExportConfig()


class LoggingConfig(BaseModel):
    level: str = Field("info", pattern="^(debug|info|warn|error)$")
    format: str = Field("json", pattern="^(json|text)$")


class StoragePathsConfig(BaseModel):
    models: str = "models"
    cache: str = ".cache"
    data: str = "data"


class StorageConfig(BaseModel):
    paths: StoragePathsConfig = StoragePathsConfig()


class SystemConfig(BaseModel):
    locale: str = "ru-RU"
    timezone: str = "Europe/Moscow"


class PerfThresholdsConfig(BaseModel):
    # Допустимое относительное падение throughput (tokens/s)
    # перед флагом регрессии
    tps_regression_pct: float = 0.12  # MXFP4 baseline
    # Допустимый относительный рост p95 decode latency (short)
    p95_regression_pct: float = 0.18
    # Жёсткий лимит отношения p95_long / p95_short (SLA)
    p95_ratio_limit: float = 1.30
    # Допустимый относительный рост отношения p95_long/short
    # vs предыдущий отчёта
    p95_ratio_regression_pct: float = 0.20


class PerfConfig(BaseModel):
    thresholds: PerfThresholdsConfig = PerfThresholdsConfig()


class RootConfig(BaseModel):
    llm: LLMConfig
    embeddings: EmbeddingsConfig
    rag: RAGConfig
    emotion: EmotionConfig
    reflection: ReflectionConfig
    metrics: MetricsConfig
    logging: LoggingConfig
    storage: StorageConfig
    system: SystemConfig
    perf: PerfConfig | None = None  # optional while rolling out

    model_config = ConfigDict(extra="forbid")


class ConfigError(Exception):
    pass


def _load_yaml_if_exists(path: pathlib.Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _merge_dict(
    base: Dict[str, Any], override: Dict[str, Any]
) -> Dict[str, Any]:
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = _merge_dict(base[k], v)
        else:
            base[k] = v
    return base


def _apply_env(cfg: Dict[str, Any]) -> None:
    prefix_len = len(ENV_PREFIX)
    for env_key, value in os.environ.items():
        if not env_key.startswith(ENV_PREFIX):
            continue
        path_parts = env_key[prefix_len:].lower().split("__")
        target = cfg
        for part in path_parts[:-1]:
            if part not in target or not isinstance(target[part], dict):
                target[part] = {}
            target = target[part]
        leaf = path_parts[-1]
        if value.lower() in {"true", "false"}:
            cast_val: Any = value.lower() == "true"
        else:
            try:
                cast_val = int(value)
            except ValueError:
                try:
                    cast_val = float(value)
                except ValueError:
                    cast_val = value
        target[leaf] = cast_val


_lock = threading.Lock()


def _resolve_config_dir() -> pathlib.Path:
    """Resolve config directory each call honoring env var changes."""
    return pathlib.Path(os.getenv("MIA_CONFIG_DIR", DEFAULT_CONFIG_DIR))


@lru_cache(maxsize=1)
def get_config() -> RootConfig:  # noqa: D401
    with _lock:
        cfg_dir = _resolve_config_dir()
        base_cfg = _load_yaml_if_exists(cfg_dir / "base.yaml")
        overrides_cfg = _load_yaml_if_exists(
            cfg_dir / "overrides.local.yaml"
        )
        merged = _merge_dict(base_cfg, overrides_cfg)
        _apply_env(merged)
        try:
            return RootConfig.model_validate(merged)
        except Exception as e:  # noqa: BLE001
            raise ConfigError(str(e)) from e


def clear_config_cache() -> None:
    """Clear cached config (primarily for tests)."""
    get_config.cache_clear()


def as_dict() -> Dict[str, Any]:
    return get_config().model_dump()
