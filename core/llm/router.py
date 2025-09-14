"""Model router mapping model_id -> (provider, pipeline) (ADR-0026).

Initial simple implementation: only primary pipeline supported; lightweight
placeholder when configured can be added later.
"""
from __future__ import annotations

from typing import Type

from core.llm.factory import get_model
from core.llm.pipeline.primary import PrimaryPipeline
from core.llm.pipeline.base import GenerationPipeline

_PIPELINES = {
    "primary": PrimaryPipeline,
}


def resolve(model_id: str, repo_root: str = ".") -> tuple[object, Type[GenerationPipeline]]:  # noqa: D401,E501
    provider = get_model(model_id, repo_root=repo_root)
    # For now assume any resolved provider is primary unless it exposes a
    # role attribute different from 'primary' later.
    try:
        role = getattr(provider.info(), "role", "primary")
    except Exception:  # noqa: BLE001
        role = "primary"
    pipeline_cls = _PIPELINES.get(role, PrimaryPipeline)
    return provider, pipeline_cls


__all__ = ["resolve"]
