"""Configuration loading and validation (S1 modular refactor).

Changes introduced in S1:
- Split monolithic RootConfig into per-module schemas under `core.config.schemas.*`.
- Added top-level `schema_version` (migration: legacy configs without it → set to 1 with warning).
- Added `modules.enabled` list to declare which modules are active (future ModuleManager).
- AggregatedConfig stores references to validated sub-schemas but is itself decoupled (type Any).

Layer order (highest precedence last merge wins):
1. base.yaml
2. overrides.local.yaml (ignore if missing)
3. ENV (prefix MIA__ using double underscore to denote nesting)

Unknown keys inside sub-schemas still rejected (validated separately after migration).
"""
from __future__ import annotations

import os
import pathlib
import threading
from functools import lru_cache
from typing import Any, Dict, List, Type

import yaml
from pydantic import BaseModel, Field, ConfigDict

# Import sub-schemas (decoupled)
from .schemas.llm import LLMConfig, PrimaryLLMConfig, LightweightLLMConfig, OptionalMoEConfig, OptionalMoETimeouts  # noqa: F401
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
        target[leaf] = cast_val


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
        print("[config-migration] schema_version missing → assuming 1")  # noqa: T201
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
                raise ConfigError(f"Validation failed for module '{name}': {e}") from e
    return validated


@lru_cache(maxsize=1)
def get_config() -> AggregatedConfig:  # noqa: D401
    with _lock:
        cfg_dir = _resolve_config_dir()
        base_cfg = _load_yaml_if_exists(cfg_dir / "base.yaml")
        overrides_cfg = _load_yaml_if_exists(cfg_dir / "overrides.local.yaml")
        merged = _merge_dict(base_cfg, overrides_cfg)
        _apply_env(merged)
        migrated = _migrate_legacy(merged)
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
