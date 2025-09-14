# ADR-0008: System Prompt Layering

Status: Draft (to be Accepted at Phase 3 start)
Date: 2025-08-26

## Context

Need stable base behavior (concise, safe answers) while allowing user persona customization without risking removal of safety / formatting rules. Single mutable prompt would mix concerns (auditing, caching, safety, UX experimentation).

## Decision

Introduce layered prompt composition:

Layer 0 (implicit safety header – future) -> Layer 1 (config llm.system_prompt.text) -> Layer 2 (session persona / role, length-limited, sanitized) -> Layer 3 (request ephemeral additions) -> Layer 4 (reasoning preset parameter overrides; not textual).

Config keys added (llm.system_prompt.*). Persona length limited by max_persona_chars. Hash(system_prompt.text) + version logged in GenerationStarted (planned). Persona not allowed to override safety instructions; if conflict detected (regex of forbidden tokens) persona is truncated with warning metric increment.

## Consequences

Pros:

- Stable hashing & versioning for reproducibility and A/B comparisons.
- Safer user experimentation (cannot delete base rules).
- Caching: tokenize Layer 1 once, append variable parts.

Cons:

- Slight complexity increase (composition logic + sanitation).
- Need additional metrics & tests.

## Tests (planned)

1. Persona empty -> effective_hash == base_hash.
2. Persona too long -> truncated length == max_persona_chars.
3. Forbidden override attempt -> blocked + metric persona_forbidden_total increment.
4. Version bump changes hash.
5. GenerationStarted includes system_prompt_version & hash.

## Metrics (planned)

- system_prompt_version{model_id}
- persona_len{name?} (histogram bucketed)
- persona_forbidden_total

## Future

- Layer 0 safety header formalization (separate file + version).
- Optional diff viewer in UI (“View Effective Prompt”).
