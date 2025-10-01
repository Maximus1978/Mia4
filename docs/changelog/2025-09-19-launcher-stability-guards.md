# 2025-09-19 Launcher Stability Guards

## Summary

Added Windows launcher smoke test (`tests/launcher/test_launcher_smoke.py`) and pattern guard ensuring `scripts/launch/run_all.bat` remains free of brittle `if (` constructs that commonly trigger `was unexpected at this time` batch parsing errors. Smoke test invokes `run_all.bat dev` headless (`MIA_NO_BROWSER=1`) asserting clean exit, presence of `UI launch URL=`, and absence of parser error signatures.

## Motivation

Recent Windows batch regressions risk silent local onboarding failures. Early CI detection protects developer experience and upholds INV-LAUNCHER-STABLE invariant for predictable dev startup.

## Details

- Test 1: Conditional Windows-only execution; XFail if `npm` absent (avoids hard failure in minimal CI images).
- Test 2: Static content guard rejecting accidental POSIX style `if (` pattern migration.
- Environment: Sets `MIA_LAUNCH_STAY=0` to allow script to terminate promptly; reuses existing venv.
- Timeout: 600s upper bound (first run may include `npm install`).

## Metrics / Observability

No new runtime metrics; test acts as preventive contract. Future enhancement may parse and assert latency banner lines.

## Risks

- First-run slowness if node modules not yet installed; mitigated via generous timeout and potential future caching strategy.
- Possible flakiness on heavily loaded CI when performing initial `npm install` (monitor and consider caching `node_modules`).

## Follow-ups

- (Optional) Introduce `MIA_SKIP_UI_BUILD=1` fast path for pure API smoke.
- Parse and assert presence of backend / frontend ready banners for richer diagnostics.

## Update (Fast Path Added)

Added environment variable `MIA_LAUNCH_SMOKE=1` to bypass all UI build / dev server logic while still emitting a canonical `UI launch URL=` line. Launcher smoke pytest now uses this for rapid CI probing without Node/npm costs.

### 2025-09-19 Patch: ASCII Echo Guard

Replaced a Unicode en dash (–) in the SMOKE mode echo line with ASCII hyphen (-). Non-ASCII characters inside parenthesized command blocks can trigger `was unexpected at this time` parsing errors in `cmd.exe` depending on current code page. New guideline: launcher `.bat` scripts must remain ASCII-only in executable lines; if Unicode needed, move it to comments outside blocks.

## Status

Shipped. Invariant INV-LAUNCHER-STABLE now enforced by tests.
