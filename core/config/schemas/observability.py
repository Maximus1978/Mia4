"""Observability schemas (metrics + logging) extracted for modularity."""
from __future__ import annotations

from pydantic import BaseModel, Field


class MetricsExportConfig(BaseModel):
    prometheus_port: int = 9090


class MetricsConfig(BaseModel):
    export: MetricsExportConfig = MetricsExportConfig()


class LoggingConfig(BaseModel):
    level: str = Field("info", pattern="^(debug|info|warn|error)$")
    format: str = Field("json", pattern="^(json|text)$")
