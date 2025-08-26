"""Modules package (S2).

Defines lightweight runtime module system to decouple core subsystems.
Current sprint scope (S2):
 - ModuleDescriptor dataclass
 - ModuleManager: loads descriptors for enabled modules from config
 - LLM module registration (others stub/no-op)

Later sprints: lifecycle hooks (warmup, shutdown), capability registry.
"""
from __future__ import annotations

from .module_manager import ModuleManager, ModuleDescriptor  # noqa: F401

__all__ = ["ModuleManager", "ModuleDescriptor"]
