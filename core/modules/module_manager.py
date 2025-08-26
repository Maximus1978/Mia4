"""ModuleManager and descriptors (S2).

Responsibilities (current scope):
 - Read enabled module names from config.modules.enabled
 - Map names to ModuleDescriptor objects (registry)
 - Initialize modules lazily on first access (defer heavy loads)
 - Unknown module names → warn & skip (forward compatibility)

Future scope (later sprints):
 - Lifecycle events (init/warmup/shutdown)
 - Capability discovery & ServiceRegistry
 - Error isolation (module crash → mark disabled)
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict, Optional, Any

from core.config import get_config
from core.registry.loader import load_manifests, verify_model_checksum
from core.llm import (
    DummyProvider,
    LlamaCppProvider,
    ModelProvider,
    ModelLoadError,
)
from core.events import emit, ModelUnloaded
import time
from threading import RLock


@dataclass(frozen=True)
class ModuleDescriptor:
    name: str
    init: Callable[[], Any]
    lazy: bool = True  # reserved flag; all current modules lazy


class ModuleState:
    __slots__ = ("descriptor", "instance", "initialized")

    def __init__(self, descriptor: ModuleDescriptor):
        self.descriptor = descriptor
        self.instance: Any | None = None
        self.initialized = False

    def get(self) -> Any:
        if not self.initialized:
            self.instance = self.descriptor.init()
            self.initialized = True
        return self.instance


class ModuleManager:
    def __init__(self, extra_registry: Optional[Dict[str, ModuleDescriptor]] = None):
        cfg = get_config()
        enabled = set(cfg.modules.enabled)
        self._states: Dict[str, ModuleState] = {}
        # base registry (S2 only llm)
        registry: Dict[str, ModuleDescriptor] = {
            "llm": ModuleDescriptor("llm", init=_init_llm_module),
        }
        if extra_registry:
            registry.update(extra_registry)
        self._unknown: list[str] = []
        for name in enabled:
            desc = registry.get(name)
            if not desc:
                # skip unknown gracefully
                self._unknown.append(name)
                continue
            self._states[name] = ModuleState(desc)

    @property
    def unknown(self) -> list[str]:  # modules mentioned but not registered
        return list(self._unknown)

    def is_enabled(self, name: str) -> bool:
        return name in self._states

    def get(self, name: str) -> Any:
        state = self._states.get(name)
        if not state:
            raise KeyError(f"Module '{name}' not enabled or not registered")
        return state.get()

    def list_enabled(self) -> list[str]:
        return list(self._states.keys())


# --- Module initializers -------------------------------------------------

def _init_llm_module() -> Any:  # noqa: ANN401 - generic
    # For now we return a lightweight facade placeholder.
    # Later this becomes a proper LLMModule orchestrating registry/providers.
    return LLMModule()


class LLMModule:
    """LLM orchestration module (S3 routing logic + S4 capabilities).

    Added in S4:
        - Capability-based routing (get_provider_by_capabilities)
    """

    def __init__(self) -> None:
        self._providers: Dict[str, ModelProvider] = {}
        self._manifest_cache: Dict[str, Any] | None = None
        self._capabilities_cache: Dict[str, tuple[str, ...]] = {}
        # Protect provider loads (double-checked locking in _load_provider)
        self._load_lock = RLock()

    # --- Provider management -------------------------------------------------
    def _load_provider(
        self,
        model_id: str,
        repo_root: str | Path = ".",
        skip_checksum: bool | None = None,
    ) -> ModelProvider:
        # Double-checked locking to avoid duplicate loads under concurrency
        prov = self._providers.get(model_id)
        if prov is not None:
            return prov
        with self._load_lock:
            prov = self._providers.get(model_id)
            if prov is not None:
                return prov
            manifests = load_manifests(repo_root)
            if model_id not in manifests:
                raise ModelLoadError(f"Unknown model id: {model_id}")
            manifest = manifests[model_id]
            cfg_llm = get_config().llm
            if skip_checksum is None:
                skip_checksum = cfg_llm.skip_checksum
            verify_model_checksum(manifest, repo_root, skip=skip_checksum)
            if str(manifest.path).endswith(".gguf"):
                primary_cfg = cfg_llm.primary
                provider = LlamaCppProvider(
                    model_path=manifest.path,
                    model_id=manifest.id,
                    role=manifest.role,
                    context_length=manifest.context_length,
                    n_gpu_layers=primary_cfg.n_gpu_layers,
                    temperature=primary_cfg.temperature,
                    top_p=primary_cfg.top_p,
                    max_output_tokens=primary_cfg.max_output_tokens,
                    n_threads=primary_cfg.n_threads,
                    n_batch=primary_cfg.n_batch,
                )
            else:
                provider = DummyProvider(
                    model_id=manifest.id,
                    role=manifest.role,
                )
            self._capabilities_cache[model_id] = tuple(manifest.capabilities)
            try:
                setattr(
                    provider,
                    "_manifest_capabilities",
                    tuple(manifest.capabilities),
                )
            except Exception:  # noqa: BLE001
                pass
            self._providers[model_id] = provider
            return provider

    def get_provider(
        self,
        model_id: str,
        repo_root: str | Path = ".",
        skip_checksum: bool = False,
    ) -> ModelProvider:
        return self._load_provider(model_id, repo_root, skip_checksum)

    def get_provider_by_role(
        self,
        role: str,
        repo_root: str | Path = ".",
        skip_checksum: bool = False,
    ) -> ModelProvider:
        cfg_llm = get_config().llm
        primary_id = cfg_llm.primary.id
        if role == "primary":
            return self.get_provider(primary_id, repo_root, skip_checksum)
        manifests = load_manifests(repo_root)
        primary_provider = self.get_provider(
            primary_id,
            repo_root,
            skip_checksum,
        )
        for m in manifests.values():
            if m.role == role:
                return self.get_provider(m.id, repo_root, skip_checksum)
        return primary_provider

    def get_provider_by_capabilities(
        self,
        required: list[str],
        repo_root: str | Path = ".",
        skip_checksum: bool = False,
    ) -> ModelProvider:
        """Select a provider whose manifest lists all required capabilities.

        Strategy:
          1. Exact match (all required contained) among loaded manifests.
          2. Fallback to primary provider.
        """
        if not required:
            return self.get_provider_by_role(
                "primary",
                repo_root,
                skip_checksum,
            )
        manifests = load_manifests(repo_root)
        # Preload primary for fallback
        primary = self.get_provider_by_role(
            "primary",
            repo_root,
            skip_checksum,
        )
        req_set = set(required)
        for m in manifests.values():
            caps = set(m.capabilities)
            if req_set.issubset(caps):
                return self.get_provider(m.id, repo_root, skip_checksum)
        return primary

    # --- Reasoning presets ---------------------------------------------------
    def apply_reasoning_overrides(
        self, base_kwargs: dict[str, object], mode: str | None
    ) -> dict[str, object]:
        if not mode:
            return dict(base_kwargs)
        presets = get_config().llm.reasoning_presets
        if mode not in presets:
            return dict(base_kwargs)
        merged = dict(base_kwargs)
        for k, v in presets[mode].items():
            merged[k] = v
        return merged

    # --- Idle sweep ----------------------------------------------------------
    def sweep_idle(self, now: float | None = None) -> list[tuple[str, str]]:
        cfg_llm = get_config().llm
        idle_conf: Dict[str, int] = {}
        for _alias, spec in cfg_llm.optional_models.items():
            if spec.enabled:
                idle_conf[spec.id] = spec.idle_unload_seconds
        if not idle_conf:
            return []
        ts = now or time.time()
        unloaded: list[tuple[str, str]] = []
        for mid, prov in list(self._providers.items()):
            timeout = idle_conf.get(mid)
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

    # --- Introspection -------------------------------------------------------
    def info(self) -> dict:
        cfg = get_config().llm
        return {
            "primary_id": cfg.primary.id if cfg else None,
            "lightweight_id": cfg.lightweight.id if cfg else None,
            "optional_count": len(cfg.optional_models) if cfg else 0,
            "loaded_providers": list(self._providers.keys()),
            "capability_routing": True,
        }


@lru_cache(maxsize=1)
def get_module_manager() -> ModuleManager:
    return ModuleManager()
