# 2025-09-16 Dev Mode & Reasoning UX Audit

## Summary
Audit uncovered partial regressions / incomplete implementations in already "completed" tasks (reasoning visualization, sampling UI clarity, separation of analysis vs final channels, KPI surface). Red flags added to `.instructions.md` to prevent silent drift.

## Findings
1. Reasoning placeholder missing until first reasoning token → breaks invariant "collapsed reasoning always present in dev".
2. Mixed analysis markers (e.g. `analysis|usersays:`) appear in final-visible area; whitespace normalization insufficient.
3. Developer mode state not synchronized between SettingsPopover and ChatWindow (stale localStorage read only on mount).
4. Cap UI shows duplicate string `Max tokens 1024  limit 1024` without progress indicator.
5. Reasoning ratio alert metric present but no UI highlight / badge.
6. Cancel UX lacks explicit cancelled badge when abort occurs late.
7. Performance panel omits first-token latency (KPI), only overall latency_ms.
8. Retention safeguard: analysis may leak into final message due to token append path not filtering channels.
9. Tool calling foundation lacks UI stub (difficult to confirm no-tool-call path).
10. Launcher admin script previously missed cwd/PYTHONPATH; fixed but dist staleness hint only in run_all.
11. Dark theme reasoning block styling inconsistent (light-theme colors used in dark context).

## Impact
- User confusion (reasoning noise blended with answer).
- Harder QA for reasoning leak heuristics.
- Risk of regressions slipping (no visual cap/alert cues).
- Violated documented invariant about channel separation.

## Planned Remediation (Next Patch Set)
| Priority | Action | Owner | Test Type |
|----------|--------|-------|-----------|
| P0 | Add DevContext + storage listener to sync dev mode across components | frontend | unit + integration |
| P0 | Sanitize reasoning text (strip service markers, inject line breaks) before display | frontend | unit (parser) |
| P0 | Separate final vs reasoning streams (distinct buffers, enforce no mixing) | frontend/back | integration SSE |
| P1 | Reasoning placeholder header always visible in dev | frontend | UI snapshot |
| P1 | Perf panel: add first_token_latency, cap_applied badge | frontend | unit |
| P1 | Cap display: replace duplicate text with progress bar / ratio | frontend | UI test |
| P1 | Reasoning ratio alert visual (color/badge) | frontend | unit |
| P2 | Cancelled state badge on last message | frontend | unit |
| P2 | Tool call stub list ("No tool calls") | frontend | unit |
| P2 | Dark-theme adjusted CSS vars for reasoning block | frontend | visual |
| P3 | Dist staleness hint parity in admin_run | scripts | script test |

## Acceptance Criteria
- No analysis/service markers appear in `.ai-message` content (regex: `analysis\|` absent).
- Placeholder reasoning header exists with text `(waiting...)` pre-generation in dev.
- Enabling/disabling developer mode via checkbox instantly updates ChatWindow.
- Perf panel includes first_token latency number under 1s for warm model (mock test).
- Cap applied scenario visually shows badge and progress >= 100%.
- All added features accompanied by unit tests; updated `.instructions.md` flags reverted to [x] with commit references.

## Metrics to Add
- `reasoning_placeholder_render_total` (dev effectiveness)
- `reasoning_sanitized_tokens_total` / `reasoning_sanitization_errors_total`
- `ui_first_token_latency_ms` (frontend measured) histogram

## Risks
- Over-sanitizing could strip legitimate model content if regex too broad.
- Added listeners on storage could cause re-render storms (mitigate with debounced state).

## Rollback Plan
Revert UI reasoning sanitation commit if user reports loss of semantic reasoning tokens; keep metric instrumentation for swift diagnosis.

---
Generated as part of audit pass; see updated `.instructions.md` for red flags linkage.
