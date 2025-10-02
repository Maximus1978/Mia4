# Copilot Guidance for MIA4

## Architecture map
- `src/mia4/api` hosts the FastAPI app; `/generate` streams Harmony channels via `PrimaryPipeline` and `HarmonyChannelAdapter`.
- `core/llm` wraps providers (llama.cpp), sampling presets, and channel sanitation; see `pipeline/primary.py` for prompt framing and cap logic.
- `core/modules/module_manager.py` loads model providers from `llm/registry/*.yaml` passports and flags config drift with `ModelPassportMismatch` events.
- `core/events` and `core/metrics` implement observability contracts (`Generation*`, `ToolCall*`, cancellations, `reasoning_leak_total`, `model_cap_hits_total`).
- `chatgpt-design-app/src` consumes SSE events (`analysis`, `commentary`, `token`, `usage`, `warning`, `end`) to render reasoning panes, CAP badges, and perf stats.

## Config & data sources
- Single source of truth is `configs/base.yaml`; override locally in `configs/overrides.local.yaml` or env vars `MIA__SECTION__KEY` (double underscores for nesting).
- Model passports live under `models/<model_id>/passport.yaml`; checksum enforcement runs during provider load and informs `/models` responses.
- System prompt and developer directives are composed in `PrimaryPipeline._build_harmony_prompt`; update `docs/Config-Registry.md` and relevant ADRs before changing behaviour.
- RAG plans live in `docs/ТЗ/RAG`; keep placeholders intact until those modules ship to avoid desync with product specs.

## Critical invariants
- Do not leak reasoning or service markers into final output; rely on adapter `process_chunk()` and `finalize()` and log anomalies via `core.metrics.inc_reasoning_leak` / `inc_channel_merge_anomaly`.
- Emit observability for every fallback: cancellations → `GenerationCancelled` + `CancelLatencyMeasured`, cap hits → `model_cap_hits_total`, fused sanitation → `inc_fused_marker_sanitization`.
- New config keys or public contracts require ADR updates plus `docs/Config-Registry.md` entries and matching tests (unit + contract markdown specs).
- Harmony sequencing is enforced (`analysis → commentary → final`); extend `tests/core/test_harmony_*` and SSE suites whenever streaming logic changes.

## Developer workflow
- Backend: activate `.venv`, install via `scripts\ensure_venv.bat`, run `pytest -q`; target suites with `pytest tests/core/test_harmony_channel_adapter.py` when touching streaming.
- UI: inside `chatgpt-design-app`, run `npm install`, `npm run dev` (Vite) or `npm run test` (Vitest) for component contracts; sanitization happens in `AIMessage` helpers.
- Integrated smoke: `scripts\launch\run_all.bat dev` spins up FastAPI + Vite; set `MIA_LAUNCH_SMOKE=1` for backend-only pipeline probe used in CI.
- Perf tooling (`scripts/perf_*.py`) writes snapshots under `reports/`; update baselines only with evidence recorded in `docs/changelog`.

## Implementation tips
- Pipeline context merges passport defaults, reasoning presets, and overrides through `PrimaryPipeline.prepare()`; keep cap logic emitting `model_cap_hits_total` and SSE usage frames.
- New providers belong in dedicated modules under `core/llm`; register through the module manager and expose `info().metadata` with passport sampling defaults.
- SSE schema changes must mirror `docs/API.md` and the UI consumer; document with markdown specs in `tests/ui` before shipping.
- Observe "documentation first": adjust ADRs, changelog, and `.instructions.md` before pushing logic that alters public behaviour.
- Launcher edits must preserve PowerShell-safe env handling and the `UI launch URL=` contract that `tests/launcher` asserts.
- Always scan current remediation items (`.instructions.md` + latest changelog) to stay aligned with active fused-marker and reasoning-none tasks.
