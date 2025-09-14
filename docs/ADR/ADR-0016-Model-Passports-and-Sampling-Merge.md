# ADR-0016: Model Passports & Sampling Merge Order

Status: Draft
Date: 2025-08-31

## Context

Different models require distinct default sampling parameters (temperature, top_p, max output tokens, stop sequences). We also have reasoning presets and user custom overrides. We need deterministic merge precedence and a versioned manifest ("passport") per model to surface provenance and enable per-model tuning without hidden code defaults.

## Decision

Introduce per-model YAML/JSON passport files stored under `models/<model_id>/passport.yaml` (exact path configurable later). Passport fields:

```yaml
model_id: <str>
passport_version: 1
hash: <sha256-of-canonical-passport-content>
sampling_defaults:
  temperature: 1.0
  top_p: 1.0
  top_k: 0
  repetition_penalty: 1.0
  max_output_tokens: 512
  stop: []  # legacy final marker removed (Harmony only)
performance_hints:
  expected_first_token_ms: 900-1200
  expected_decode_tps: 40-50
  recommended_n_ctx: 8192
reasoning:
  default_reasoning_max_tokens: 256
  # marker removed (Harmony channels provide structure)
capabilities:
  supports_harmony_tags: false
notes: |
  Free form description / provenance.
```

Merge precedence (lowest → highest):

1. Passport `sampling_defaults`
2. Reasoning preset adjustments (e.g. lowering max_output_tokens or temperature)
3. User custom overrides (explicit request overrides)

Each effective sampling parameter carries an `origin` marker in `GenerationStarted.sampling_origin` map.

Emit hashes + versions:

- `passport.hash`, `passport.version`
- `system_prompt.hash`, `system_prompt.version`
- (Later) `app_persona.hash`, `app_persona.version`

## Consequences

- Transparent source of each runtime sampling value → reproducibility.
- Changing passport requires version bump → easier diff & perf attribution.
- Simplifies future A/B by swapping passports.

## Alternatives Considered

- Hardcode defaults in code (rejected: opaque, hard to diff).
- Single global defaults (rejected: model-specific divergence needed).

## Testing

- Unit: merge precedence matrix.
- Integration: switching model updates effective defaults; origin flags correct.

## Open Issues

- Distribution format (YAML vs JSON) – start with YAML for readability.
- Signing passports (future security ADR).

## Status Transition

Draft → Accepted after initial implementation & tests.
