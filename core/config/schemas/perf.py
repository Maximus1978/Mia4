"""Perf module config schema (S1)."""
from __future__ import annotations

from pydantic import BaseModel


class PerfThresholdsConfig(BaseModel):
    tps_regression_pct: float = 0.12
    p95_regression_pct: float = 0.18
    p95_ratio_limit: float = 1.30
    p95_ratio_regression_pct: float = 0.20


class PerfConfig(BaseModel):
    thresholds: PerfThresholdsConfig = PerfThresholdsConfig()
