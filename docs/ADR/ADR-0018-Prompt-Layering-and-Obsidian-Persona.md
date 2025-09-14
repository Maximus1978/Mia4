# ADR-0018: Prompt Layering & Obsidian Persona Integration

Status: Draft
Date: 2025-08-31

## Context

We require consistent, inspectable composition of the final system prompt while enabling model-specific adjustments (passports) and an application persona authored in Obsidian. Current approach injects a marker and reasoning tag ad-hoc.

## Decision

Introduce layered prompt assembly pipeline:

1. `base_system` (static, versioned in config)
2. `model_passport_fragment` (optional; guidance for specific model quirks)
3. `app_persona` (read-only sync from Obsidian file; hashed)
4. `dynamic_reasoning_tag` (Reasoning: \<level\>)
5. `user_message`

Each layer recorded with hash+version in `GenerationStarted` event: `system_prompt_hash`, `passport_hash`, `app_persona_hash`.

Obsidian integration (minimal Sprint 3C scope):

- Config keys: `obsidian.enabled`, `obsidian.vault_path`, `obsidian.persona_file`.
- On startup (and manual reload endpoint) read file, normalize (trim trailing spaces), compute hash.
- Failure to load persona: emit warning event, continue without layer.

## Consequences

- Reproducible prompt semantics; diffs attributable to specific layer changes.
- Safe introduction of model-specific prompt guidance without diverging global style.

## Alternatives Considered

- Single concatenated file (hard to attribute changes) – rejected.
- Dynamic in-DB storage (premature complexity) – deferred.

## Testing

- Unit: layering order stable, hashes change only when layer content changes.
- Integration: GenerationStarted includes correct hash set with persona present/absent.

## Open Issues

- Live file watch vs manual reload (start with manual to avoid cross-platform complexity).
- Persona size limit enforcement & truncation policy.

## Status Transition

Draft → Accepted after initial layering + persona hash emission implemented.
