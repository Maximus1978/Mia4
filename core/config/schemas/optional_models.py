"""Optional models shared schema placeholder (future use).

For now optional LLM models remain under `llm.optional_models`.
"""
from __future__ import annotations

from pydantic import BaseModel


class OptionalModelsConfig(BaseModel):
    # Placeholder for cross-module optional model declarations.
    pass
