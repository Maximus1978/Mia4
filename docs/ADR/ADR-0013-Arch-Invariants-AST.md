# ADR-0013: Architectural Invariants via AST Graph

Status: Accepted (2025-08-26)

## Context

Previous ad-hoc or regex-based import validations were brittle. We need a
repeatable static analysis to enforce layering (e.g. `core.llm` must not import
`memory`, scripts not imported by core, etc.).

## Decision

Implement an AST-based import graph builder used in tests to assert forbidden
edges. Rules captured in test (`tests/core/test_arch_import_graph_rules.py`).

## Rules (Initial)

- No imports from `scripts` into `core/*` packages.
- `core.llm` must not import `memory` or `modules` internals (only public interfaces planned).
- Cycles disallowed (graph traversal check).

## Enforcement

Test constructs graph (nodes=modules, edges=import). Fails on first forbidden
edge or cycle. Fast (single pass) and hermetic (no execution side-effects).

## Consequences

- Early detection of layering violations.
- Provides base for future guards (size limits, public API whitelist).
- Static analysis can miss dynamic imports; mitigation: runtime audit (deferred).

## Alternatives Considered

- Runtime monkeypatch to log imports (slow, order-dependent) — rejected.
- Flake8 plugin custom rule — heavier to maintain; may add later for editor feedback.

## Future Work

- Auto-generate a DOT diagram for docs.
- Enforce public API boundaries (only modules' __all__).
- Track module size metrics.
