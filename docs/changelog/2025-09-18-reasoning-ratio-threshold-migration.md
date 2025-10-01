# 2025-09-18 Reasoning Ratio Threshold Migration

Status: Shipped

## Summary

Established `llm.postproc.reasoning.ratio_alert_threshold` as authoritative config key (already present in schema & base.yaml) and codified round-trip exposure through `/config` endpoint.

## Artifacts

- Added `docs/Config-Registry.md` entry documenting the key.
- Added API contract test `test_config_reasoning_ratio_threshold_round_trip.py` verifying backend ↔ UI value consistency.

## Rationale

Ensures single source of truth for reasoning ratio alert threshold (INV-CONFIG-BIDIR) and prevents silent drift between backend config and UI logic.

## Test Coverage

- Round-trip test asserts numeric value, equality with backend, and broad sanity range.

## Follow-ups

- If future dynamic adjustments (per-model thresholds) are introduced, extend `/config` with model-scoped overrides + ADR addendum.

## Risks

Low — purely declarative migration + test; no runtime behaviour change.
