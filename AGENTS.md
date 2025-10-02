# AGENTS

## Purpose
- Give assistants a fast, accurate mental model of the MIA4 stack and working agreements before touching code.
- Capture invariants encoded in docs, ADRs, and tests so Harmony channel separation, observability, and UX contracts stay intact.

## Top-Level Architecture
- `src/mia4/api`: FastAPI surface for `/health`, `/config`, `/models`, `/generate` SSE streaming, and abort handling. Depends on `core` subsystems for metrics, config, and modules.
- `core/config`: Pydantic-backed loader. Reads `configs/base.yaml`, merges env overrides via `MIA__` prefix, exposes structured objects through `get_config()`.
- `core/registry`: Model manifests (`llm/registry/*.yaml`) plus checksum verification, feeding ModuleManager for lazy provider loads.
- `core/llm`: Providers (llama.cpp wrapper), pipelines (`pipeline/primary.py`), Harmony adapters, post-processing guards, sampling presets, and metrics hooks.
- `core/events`: In-process event bus and typed events (`GenerationStarted`, `GenerationCompleted`, `ModelLoaded`, etc.) for observability and assertions.
- `chatgpt-design-app`: Vite/React UI consuming SSE events (`analysis`, `commentary`, `token`, `usage`, `end`) to drive CAP ratio, reasoning badges, and dev toggles.
- `tests/`: pytest suites across core, API, integration, perf, and UI contract markdown specs. Read nearby tests before refactors; they encode current behaviour.

## Harmony and Reasoning Quick Reference
- Prompt builder (`PrimaryPipeline._build_harmony_prompt`) injects the fixed system block (identity, cutoff, current date, reasoning level, channel contract), developer instructions, sliding session history, and the current user turn.
- Streaming adapter (`HarmonyChannelAdapter`) enforces channel order `analysis -> commentary -> final`, normalises `<|return|>`, tracks per-channel token counts, and emits leakage metrics (`reasoning_leak_total`, `channel_merge_anomaly_total`).
- Commentary retention modes (metrics_only, hashed_slice, redacted_snippets, raw_ephemeral) live in config; see ADR-0033. Tool chains may override the mode when commentary includes tool chatter.
- Final sanitation guard scrubs stray `<|...|>` markers and records `reason=service_marker_in_final` or `finalize_sanitize`.

## Configuration and Environments
- Base config: `configs/base.yaml`. Local overrides belong in `configs/overrides.local.yaml` (git-ignored).
- Environment overrides: `MIA__SECTION__KEY=value` (double underscores). Tests call `reset_for_tests()` to clear cached config between runs.
- Reasoning presets are exposed via `/presets`; selection is recorded through `ReasoningPresetApplied`, and `apply_reasoning_overrides` whitelists supported provider kwargs.
- Model passports (`models/<id>/passport.yaml`) describe capabilities, default reasoning budgets, and sampling defaults.

## Observability Essentials
- Metrics are required for new behaviour. Use `core.metrics` helpers for channel anomalies, commentary retention, cancel latency, etc. `snapshot()` output is widely asserted in tests.
- Event bus is first-class: emit `GenerationStarted`, `ModelRouted`, `GenerationCompleted`, `GenerationCancelled`, `ToolCallPlanned`, `ToolCallResult`, and friends per ADR contracts.
- SSE stream contract lives in `docs/API.md`; when adding events or fields, update tests and docs together.
- Changelogs (`docs/changelog/*.md`) record rollout history and TODOs. Review relevant entries before extending a feature.

## Testing Strategy
- Default command: `pytest -q`. Target suites exist for harmony parsing, channel isolation, tool calling, config validation, perf guards, and UI contracts (`tests/core/test_harmony_*`, `tests/api/test_generate_*`, etc.).
- Perf tests in `tests/perf` assert metrics only; avoid running heavy probes unless the change touches perf-critical code.
- UI markdown specs under `tests/ui/*.md` outline acceptance criteria; align React changes with these narratives.
- New tests should mirror existing fixture style (`tmp_path`, `TestClient(app)`, `reset_for_tests()`) and prefer end-to-end coverage over mocking.

## Workflow Agreements
- Always read `.instructions.md` (UTF-8). If glyphs look corrupted, re-open with a UTF-8 aware editor. Treat it as the single source of truth for style rules.
- Follow "observability first": instrument metrics and events before or alongside feature logic, never afterwards.
- Keep docs in sync: ADR for design intent, dated changelog entry for shipped behaviour, API/config docs for contract changes.
- Review and respect TODOs in ADRs and changelogs; either address them or document why they remain.
- Prefer `rg` for search and PowerShell `Get-Content -Raw` for multi-line inspection to avoid shell pitfalls.

## Collaboration Notes
- Sprint rhythm: curate a backlog of bite-sized tasks. For each, confirm scope, affected docs, and acceptance signals before implementation.
- Deliverables per task: code plus updated docs/tests, pytest evidence (or mitigation plan if tests cannot run), and manual UI validation steps for the user.
- End of sprint: consolidate completed tasks, ensure changelog coverage, then prepare one clean commit with a precise message and push.
- When uncertain about config keys, channel behaviour, or retention rules, clarify early; tests aggressively guard against regressions.

## Reference Map
- ADRs: `docs/ADR` (channel separation v2, SSE warning frame, reasoning presets, tool calling scope, config invariants).
- Changelogs: `docs/changelog` track Harmony milestones, CAP badges, cancellation flow, finalize sanitation guard, and open follow-ups.
- Specs and backlog: `docs` contains a subfolder whose name is the Cyrillic letters "TZ"; it holds product specs, sprint plans, and UX notes. Translate when needed for external communication.
- Scripts: `scripts/` hosts perf baselines, launch helpers (`ensure_venv.bat`, `run_all.bat`), and debugging tools (`stability_probe.py`).

## When to Read What

### 🆕 **First Time Here?**
1. Read **AGENTS.md** (this file) → Architecture overview + invariants
2. Read **`.instructions.md`** → Core principles + working style
3. You're ready to start!

### 🚀 **Starting a Sprint / New Bug?**
1. Read **`SPRINT.md`** → Current context, active tasks, root cause analysis
2. Check "Next Steps" section → Know exactly what to do
3. Review "Risks & Mitigations" → Understand blockers

### 🔄 **Continuing Work?**
1. Check **`SPRINT.md`** "Active Tasks" → See progress
2. Update completed tasks in `SPRINT.md`
3. Add new findings to "Notes & Observations"

### 📚 **Need Reference?**
- **Architecture / Config / Testing** → `AGENTS.md` (this file)
- **Principles / Rules / Workflow** → `.instructions.md`
- **Current sprint details** → `SPRINT.md`
- **ADRs** → `docs/ADR/` for design decisions
- **Changelogs** → `docs/changelog/` for feature history

---

## Getting Started Checklist for Agents

1. Read `SPRINT.md` to understand current sprint goal and active tasks.
2. Identify affected files from "Implementation Plan" section.
3. Check affected tests and docs; update acceptance markdown if UI or API changes.
4. Implement changes with metrics and event instrumentation in place.
5. Run targeted pytest suites plus any smoke or perf checks required; collect results.
6. Prepare manual UI validation steps (reasoning ratio badges, CAP indicators, cancellation UX, etc.).
7. Update `SPRINT.md`: mark completed tasks, add new findings, update "Next Steps".
8. Summarise work, highlight risks, note outstanding follow-ups, and stage for commit.

