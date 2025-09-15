"""RAG config schema (S1)."""
from __future__ import annotations

from pydantic import BaseModel


class RAGHybridConfig(BaseModel):
    weight_semantic: float = 0.6
    weight_bm25: float = 0.4


class RAGNormalizeConfig(BaseModel):
    # Registry alignment: method/epsilon fields present
    method: str = "minmax"  # minmax | zscore
    epsilon: float = 1e-6
    min_score: float = 0.0
    max_score: float = 1.0


class RAGContextConfig(BaseModel):  # fraction of window for RAG insert
    max_fraction_of_window: float = 0.80


class RAGExpansionConfig(BaseModel):  # query expansion settings
    enabled: bool = False
    model: str = "lightweight"


class RAGConfig(BaseModel):
    enabled: bool = True
    collection_default: str = "memory"
    top_k: int = 8
    hybrid: RAGHybridConfig = RAGHybridConfig()
    normalize: RAGNormalizeConfig = RAGNormalizeConfig()
    context: RAGContextConfig = RAGContextConfig()
    expansion: RAGExpansionConfig = RAGExpansionConfig()
