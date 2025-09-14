"""Legacy factory delegating to LLMModule (post S3).

NOTE: This layer remains for backward compatibility with existing imports.
All logic (routing, reasoning presets, idle sweep) lives in `LLMModule`.
Will be removed once call sites migrate to `core.modules` usage directly.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple
from core.llm import ModelProvider
from core.modules.module_manager import get_module_manager  # S6 temp dep
import time
from core.events import emit, ModelUnloaded


def sweep_idle(
    idle_config: dict[str, int] | None = None, now: float | None = None
) -> List[Tuple[str, str]]:  # noqa: D401
    """Backward compatible idle sweep.

    If explicit idle_config provided (legacy path) operate directly over
    providers loaded via LLMModule; else delegate to module's own optional
    models based sweep.
    """
    llm_mod = get_module_manager().get("llm")
    if not idle_config:
        return llm_mod.sweep_idle(now=now)
    ts = now or time.time()
    unloaded: List[Tuple[str, str]] = []
    for mid, prov in list(
        llm_mod._providers.items()
    ):  # type: ignore[attr-defined]
        timeout = idle_config.get(mid)
        if not timeout or timeout <= 0:
            continue
        last_used = getattr(prov, "last_used", None)
        if last_used is None:
            continue
        if ts - last_used >= timeout:
            prov.unload()
            emit(
                ModelUnloaded(
                    model_id=prov.info().id,
                    role=prov.info().role,
                    reason="idle",
                    idle_seconds=int(ts - last_used),
                )
            )
            unloaded.append((mid, "idle"))
    return unloaded


_LAST_CFG_DIR: str | None = None


def get_model(
    model_id: str, repo_root: str | Path = ".", skip_checksum: bool = False
) -> ModelProvider:  # noqa: D401
    global _LAST_CFG_DIR
    # If config dir changes between calls (tests mutate env), clear cache
    import os  # local import to avoid upfront cost
    cur_dir = os.getenv("MIA_CONFIG_DIR") or "configs"
    if _LAST_CFG_DIR is not None and _LAST_CFG_DIR != cur_dir:
        try:
            get_module_manager.cache_clear()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
    _LAST_CFG_DIR = cur_dir
    llm_mod = get_module_manager().get("llm")
    return llm_mod.get_provider(
        model_id, repo_root=repo_root, skip_checksum=skip_checksum
    )


def clear_provider_cache() -> None:  # noqa: D401
    # New module instance holds cache; just reset ModuleManager singleton
    from functools import lru_cache as _lc  # noqa: F401
    get_module_manager.cache_clear()  # type: ignore[attr-defined]


def get_model_by_role(
    role: str, repo_root: str | Path = ".", skip_checksum: bool = False
) -> ModelProvider:  # noqa: D401
    llm_mod = get_module_manager().get("llm")
    return llm_mod.get_provider_by_role(
        role, repo_root=repo_root, skip_checksum=skip_checksum
    )


def apply_reasoning_overrides(
    base_kwargs: dict[str, object], mode: str | None
) -> dict[str, object]:  # noqa: D401
    llm_mod = get_module_manager().get("llm")
    return llm_mod.apply_reasoning_overrides(base_kwargs, mode)
