"""Configuration loading & validation (S1 refactor).

Changes S1:
- Split RootConfig into per-module schemas (`core.config.schemas.*`).
- Added `schema_version` (legacy missing → assume 1, warn).
- Added `modules.enabled` (future ModuleManager).
- AggregatedConfig holds validated sub-schemas (opaque here).

Precedence (last wins): base.yaml → overrides.local.yaml → ENV (MIA__*).

Unknown sub-schema keys still rejected post‑migration.
"""
from __future__ import annotations

import os
import pathlib
import threading
from functools import lru_cache
from typing import Any, Dict, List, Type

import yaml
from core import metrics
from core.errors import validate_error_type
from pydantic import BaseModel, Field, ConfigDict

# Import sub-schemas (decoupled)
from .schemas.llm import LLMConfig  # noqa: F401
from .schemas.rag import RAGConfig  # noqa: F401
from .schemas.perf import PerfConfig  # noqa: F401
from .schemas.core import (
    EmbeddingsConfig,
    EmotionConfig,
    ReflectionConfig,
    StorageConfig,
    SystemConfig,
)
from .schemas.observability import MetricsConfig, LoggingConfig


class ModulesConfig(BaseModel):
    enabled: List[str] = Field(default_factory=list)


class AggregatedConfig(BaseModel):
    schema_version: int = 1
    modules: ModulesConfig = ModulesConfig()
    # Sub-schemas (opaque to this layer → Any)
    llm: Any | None = None
    embeddings: Any | None = None
    rag: Any | None = None
    emotion: Any | None = None
    reflection: Any | None = None
    metrics: Any | None = None
    logging: Any | None = None
    storage: Any | None = None
    system: Any | None = None
    perf: Any | None = None  # optional while rolling out

    model_config = ConfigDict(extra="forbid")


DEFAULT_CONFIG_DIR = "configs"
ENV_PREFIX = "MIA__"

LEGACY_MODULE_KEYS = [
    "llm",
    "embeddings",
    "rag",
    "emotion",
    "reflection",
    "metrics",
    "logging",
    "storage",
    "system",
    "perf",
]

SUB_SCHEMA_CLASSES: Dict[str, Type[BaseModel]] = {
    "llm": LLMConfig,
    "embeddings": EmbeddingsConfig,
    "rag": RAGConfig,
    "emotion": EmotionConfig,
    "reflection": ReflectionConfig,
    "metrics": MetricsConfig,
    "logging": LoggingConfig,
    "storage": StorageConfig,
    "system": SystemConfig,
    "perf": PerfConfig,
}


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
        # Apply override
        target[leaf] = cast_val
    # Metrics + structured log (stdout; future: replace with logging module)
        dotted_path = ".".join(path_parts)
        try:
            metrics.inc("env_override_total", {"path": dotted_path})
        except Exception:  # pragma: no cover - safety
            pass
        print(
            f"[config-env-override] path={dotted_path} value=*** source=env"
        )  # noqa: T201


_lock = threading.Lock()


def _resolve_config_dir() -> pathlib.Path:
    """Resolve config directory each call honoring env var changes."""
    return pathlib.Path(os.getenv("MIA_CONFIG_DIR", DEFAULT_CONFIG_DIR))


def _migrate_legacy(data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply in-place migrations for legacy configs (no schema_version).

    Rules:
    - If `schema_version` absent → set to 1 and emit warning.
    - If `modules` absent → infer enabled list from present legacy module keys.
    """
    if "schema_version" not in data:
        # Simple stdout warn (observability module not yet abstracted here)
        print(
            "[config-migration] schema_version missing → assuming 1"
        )  # noqa: T201
        data["schema_version"] = 1
    if "modules" not in data:
        enabled = [k for k in LEGACY_MODULE_KEYS if k in data]
        data["modules"] = {"enabled": enabled}
    else:
        # ensure key exists
        data.setdefault("modules", {}).setdefault("enabled", [])
    return data


def _validate_sub_schemas(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Validate each known module via its schema class.

    Returns dict of validated objects to be attached to AggregatedConfig.
    """
    validated: Dict[str, Any] = {}
    for name, cls in SUB_SCHEMA_CLASSES.items():
        if name in raw:
            try:
                validated[name] = cls.model_validate(raw[name])
            except Exception as e:  # noqa: BLE001
                raise ConfigError(
                    f"Validation failed for module '{name}': {e}"
                ) from e
    return validated


def _normalize_and_validate(raw: Dict[str, Any]) -> None:
    """Apply cross-field normalizations and bounds validation.

    Emits metrics on violations and raises ConfigError if any hard errors.
    Normalizations:
      - llm.primary.n_gpu_layers: if int < 0 -> 0 (clip); leave 'auto' as is.
    Validations (error → raise):
      - llm.primary.top_p in (0, 1] (strict lower bound >0)
      - llm.primary.max_output_tokens > 0
    Temperature already validated by schema.
    """
    errors: list[tuple[str, str, str]] = []  # (path, code, msg)
    # n_gpu_layers normalization
    try:
        ngl = raw.get("llm", {}).get("primary", {}).get("n_gpu_layers")
        if isinstance(ngl, int) and ngl < 0:
            raw["llm"]["primary"]["n_gpu_layers"] = 0
    except Exception:  # pragma: no cover
        pass

    # top_p range
    try:
        top_p = raw.get("llm", {}).get("primary", {}).get("top_p")
        if top_p is not None and not (0 < top_p <= 1):
            errors.append(
                (
                    "llm.primary.top_p",
                    "config-out-of-range",
                    "top_p must be 0<..<=1",
                )
            )
    except Exception:  # pragma: no cover
        pass

    # max_output_tokens positive
    try:
        mot = raw.get("llm", {}).get("primary", {}).get("max_output_tokens")
        if mot is not None and mot <= 0:
            errors.append(
                (
                    "llm.primary.max_output_tokens",
                    "config-out-of-range",
                    ">0 required",
                )
            )
    except Exception:  # pragma: no cover
        pass

    if errors:
        for path, code, _ in errors:
            try:
                metrics.inc(
                    "config_validation_errors_total",
                    {"path": path, "code": code},
                )
            except Exception:  # pragma: no cover
                pass
        # Validate error codes exist
        for _, code, _ in errors:
            validate_error_type(code)
        # Aggregate message
        details = ", ".join(f"{p}:{c}:{m}" for p, c, m in errors)
        raise ConfigError(f"config validation failed: {details}")


@lru_cache(maxsize=1)
def get_config() -> AggregatedConfig:  # noqa: D401
    with _lock:
        cfg_dir = _resolve_config_dir()
        base_cfg = _load_yaml_if_exists(cfg_dir / "base.yaml")
        overrides_cfg = _load_yaml_if_exists(cfg_dir / "overrides.local.yaml")
        merged = _merge_dict(base_cfg, overrides_cfg)
        _apply_env(merged)
        migrated = _migrate_legacy(merged)
        _normalize_and_validate(migrated)
        # Validate sub-schemas before building aggregator
        validated_sub = _validate_sub_schemas(migrated)
        try:
            agg = AggregatedConfig.model_validate(migrated)
        except Exception as e:  # noqa: BLE001
            raise ConfigError(str(e)) from e
        # Attach validated objects
        for k, v in validated_sub.items():
            setattr(agg, k, v)
        return agg


def clear_config_cache() -> None:
    """Clear cached config (primarily for tests)."""
    get_config.cache_clear()


def as_dict() -> Dict[str, Any]:
    return get_config().model_dump()
