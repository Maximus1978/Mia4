"""RAG config schema (S1)."""
from __future__ import annotations

from pydantic import BaseModel


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
