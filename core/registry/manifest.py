"""Model manifest schema (Step 5)."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, field_validator, ConfigDict


class ModelManifest(BaseModel):
    id: str
    family: str
    role: str
    path: str
    quant: Optional[str] = None
    context_length: int
    capabilities: List[str]
    checksum_sha256: str
    revision: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("id")
    @classmethod
    def _id_not_empty(cls, v: str) -> str:  # noqa: D401
        if not v.strip():
            raise ValueError("id cannot be empty")
        return v

    def resolve_model_path(self, repo_root: Path) -> Path:
        p = Path(self.path)
        if not p.is_absolute():
            p = repo_root / p
        return p
