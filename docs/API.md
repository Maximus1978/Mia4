# MIA4 API (Phase 2 MVP)

Endpoints

Cross-links:

- Events contract: `Ð¢Ð—/Events.md`
- Config registry (sampling, postproc keys): `Ð¢Ð—/Config-Registry.md`
- Model passports details: `Ð¢Ð—/passports/`
- Postprocessing ADR: `ADR/ADR-0014-Postprocessing-Reasoning-Split.md`
- Sampling merge ADR: `ADR/ADR-0016-Model-Passports-and-Sampling-Merge.md`
- Prompt layering draft: `ADR/ADR-0018-Prompt-Layering-and-Obsidian-Persona.md`

## GET /health

Response: `{ "status": "ok" }`

## GET /config

Response: `{ "ui_mode": "admin"|"user" }` (controlled by env `MIA_UI_MODE`, not a config key)

## GET /presets

Expose reasoning presets for UI alignment.

Response:

```json
{
  "reasoning_presets": {
    "low": { "temperature": 0.6, "top_p": 0.9, "reasoning_max_tokens": 128 },
    "medium": { "temperature": 0.7, "top_p": 0.92, "reasoning_max_tokens": 256 },
    "high": { "temperature": 0.85, "top_p": 0.95, "reasoning_max_tokens": 512 }
  }
}
```

## GET /models

Response:

```json
{
  "models": [
    {
      "id": "gpt-oss-20b-mxfp4",
      "role": "primary",
      "capabilities": ["chat", "judge", "plan", "long_context"],
      "context_length": 32768,
      "flags": {
        "experimental": false,
        "deprecated": false,
        "alias": false,
        "reusable": true,
        "internal": false,
        "stub": false
      },
      "passport": {
        "hash": "sha256:...",
        "version": 1
      },
      "system_prompt": {
        "hash": "sha256:...",
        "version": 3
      }
    }
  ]
}
```

## POST /generate (SSE)

Request JSON:

```json
{
  "session_id": "uuid-or-string",
  "model": "model_id",
  "prompt": "text",
  "overrides": {
    "reasoning_preset": "fast",
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
    "repeat_penalty": 1.1,
    "min_p": 0.05,
    "typical_p": 0.95,
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
    "repeat_last_n": 64,
    "penalize_nl": true,
    "seed": 12345,
    "mirostat": 0,
    "mirostat_tau": 5.0,
    "mirostat_eta": 0.1,
    "max_output_tokens": 128
  }
}
```

Response (SSE frames):

Mandatory / current:

- `event: token` data: `{ seq:int, text:str, tokens_out:int, request_id, model_id }` (final channel userâ€‘visible deltas)
- `event: analysis` data: `{ request_id, model_id, text:str }` (Harmony reasoning channel; NOT persisted; may be suppressed in minimal mode)
- `event: usage` data: `{ request_id, model_id, prompt_tokens:int, output_tokens:int, latency_ms:int, first_token_latency_ms:int?, decode_tps:float, context_used_tokens:int?, context_total_tokens:int?, context_used_pct:float?, reasoning_tokens:int?, final_tokens:int?, reasoning_ratio:float?, cap_applied:bool?, effective_max_tokens:int? }`
- `event: final` data: `{ request_id, model_id, text:str, reasoning_tokens:int?, final_tokens:int?, reasoning_ratio:float?, stop_reason?:str, cap_applied?:bool, effective_max_tokens?:int, first_token_latency_ms?:int }` (authoritative sanitized final text; UI must prefer this over concatenated token deltas)
- `event: warning` data: `{ event: "ModelPassportMismatch", field:str, passport_value:int, config_value:int, request_id, model_id }`
- `event: error` data: `{ request_id, model_id, code, error_type, message }`
- `event: end` data: `{ request_id, status:"ok"|"error" }`

Tool calling (Harmony tool channel):

- `event: commentary` may include a JSON stringified tool result payload (synthetic for MVP) with shape `{tool, status, ok, error_type?, message?, preview_hash?, args_redacted?, raw_args?}` depending on retention mode.
- Internal events (not SSE) emitted on bus: `ToolCallPlanned{request_id,tool,args_preview_hash,seq}` then `ToolCallResult{request_id,tool,status,latency_ms,seq,error_type?,message?}`.
- Payload size limit configurable: `llm.tool_calling.max_payload_bytes` (default 8192). Oversize â†’ `status=error`, `error_type=tool_payload_too_large`.
- Malformed JSON â†’ `status=error`, `error_type=tool_payload_parse_error`.
- Retention modes (`llm.tool_calling.retention.mode`):
  - `metrics_only` (no tool result body beyond status commentary line)
  - `hashed_slice` (includes `preview_hash`)
  - `redacted_snippets` (hash + `args_redacted` placeholder)
  - `raw_ephemeral` (hash + trimmed raw args â€“ debug only)

Final token accounting guarantee:
Adapter flushes any undispatched final deltas on `finalize()` so `final_tokens == count(token events)` always holds.

Legacy / conditional:

- `event: reasoning` (legacy marker mode only; buffered full reasoning text when `drop_from_history=false`). New Harmony path uses streaming `analysis` events instead.


Sampling metadata:

Ð’ ÑÐ¾Ð±Ñ‹Ñ‚Ð¸ÑÑ… `GenerationStarted` Ð¸ `GenerationCompleted.result_summary.sampling` Ð¿Ñ€Ð¸ÑÑƒÑ‚ÑÑ‚Ð²ÑƒÐµÑ‚ Ð¾Ð±ÑŠÐµÐºÑ‚:

```json
{
  "temperature": 0.7,
  "top_p": 0.9,
  "top_k": 40,
  "repeat_penalty": 1.1,
  "min_p": 0.05,
  "typical_p": 0.95,
  "presence_penalty": 0.0,
  "frequency_penalty": 0.0,
  "repeat_last_n": 64,
  "penalize_nl": true,
  "seed": 12345,
  "mirostat": 0,
  "mirostat_tau": 5.0,
  "mirostat_eta": 0.1,
  "max_tokens": 128,
  "filtered_out": ["min_p"]
}
```

ÐŸÐ¾Ð»Ðµ `filtered_out` (ÐµÑÐ»Ð¸ Ð½Ðµ Ð¿ÑƒÑÑ‚Ð¾) Ð¿Ð¾ÐºÐ°Ð·Ñ‹Ð²Ð°ÐµÑ‚ ÐºÐ°ÐºÐ¸Ðµ Ð¿ÐµÑ€ÐµÐ´Ð°Ð½Ð½Ñ‹Ðµ ÐºÐ»Ð¸ÐµÐ½Ñ‚Ð¾Ð¼ Ð¿Ð°Ñ€Ð°Ð¼ÐµÑ‚Ñ€Ñ‹ Ð±Ñ‹Ð»Ð¸ Ð¾Ñ‚Ð±Ñ€Ð¾ÑˆÐµÐ½Ñ‹ Ñ‚ÐµÐºÑƒÑ‰ÐµÐ¹ Ð²ÐµÑ€ÑÐ¸ÐµÐ¹ `llama_cpp` (Ð½Ðµ Ð¿Ð¾Ð´Ð´ÐµÑ€Ð¶Ð¸Ð²Ð°ÑŽÑ‚ÑÑ ÐµÑ‘ ÑÐ¸Ð³Ð½Ð°Ñ‚ÑƒÑ€Ð¾Ð¹). Ð­Ñ‚Ð¾ Ð¿Ð¾Ð¼Ð¾Ð³Ð°ÐµÑ‚ Ð´Ð¸Ð°Ð³Ð½Ð¾ÑÑ‚Ð¸Ñ€Ð¾Ð²Ð°Ñ‚ÑŒ Ð½ÐµÑÐ¾Ð¾Ñ‚Ð²ÐµÑ‚ÑÑ‚Ð²Ð¸Ðµ Ð½Ð°ÑÑ‚Ñ€Ð¾ÐµÐº.

Sampling origins (Sprint 3A):

`GenerationStarted.sampling_origin` (and per-field annotation) shows source precedence: `passport` < `preset` < `custom`.

Merged sampling object (`GenerationStarted.sampling`) also carries `filtered_out` plus explicit `max_tokens` (alias of effective `max_output_tokens`) and is mirrored in `GenerationCompleted.result_summary.sampling`.

Reasoning & Harmony channels (ÐµÐ´Ð¸Ð½ÑÑ‚Ð²ÐµÐ½Ð½Ñ‹Ð¹ Ñ€ÐµÐ¶Ð¸Ð¼):

- Model emits structured channel tokens (Harmony format) internally; adapter extracts `analysis` vs `final`.
- `analysis` deltas stream as separate SSE events and are excluded from session history regardless of `drop_from_history`.
- `commentary` (pass-through, Ð½Ðµ ÑÑ‡Ð¸Ñ‚Ð°ÑŽÑ‚ÑÑ Ð² reasoning/final Ñ‚Ð¾ÐºÐµÐ½Ñ‹) Ð¼Ð¾Ð¶ÐµÑ‚ Ð¿Ð¾ÑÐ²Ð»ÑÑ‚ÑŒÑÑ Ð´Ð»Ñ Ð¿Ð¾Ð»ÑŒÐ·Ð¾Ð²Ð°Ñ‚ÐµÐ»ÑŒÑÐºÐ¸Ñ… Ð¿Ñ€ÐµÐ°Ð¼Ð±ÑƒÐ» (action plan) Ð¸ Ð¾Ñ‚Ð¾Ð±Ñ€Ð°Ð¶Ð°ÐµÑ‚ÑÑ ÐºÐ°Ðº `event: commentary`.
- `reasoning_tokens` counts whitespaceâ€‘split analysis tokens up to `postproc.reasoning.max_tokens` (or preset override `reasoning_max_tokens`).
- `final_tokens` counts userâ€‘visible tokens (token events).
- `reasoning_ratio = reasoning_tokens / (reasoning_tokens + final_tokens)` (0 if denominator 0).
- Alert threshold configured via `llm.postproc.reasoning.ratio_alert_threshold`; crossings increment alert metric.
- Metric `reasoning_buffer_latency_ms` retained (legacyâ€”may read 0 when no buffering occurred).

Legacy marker Ñ€ÐµÐ¶Ð¸Ð¼ ÑƒÐ´Ð°Ð»Ñ‘Ð½; Ð¿Ñ€Ð¸ Ð¾Ñ‚ÑÑƒÑ‚ÑÑ‚Ð²Ð¸Ð¸ Harmony ÑÐ¿ÐµÑ†â€‘Ñ‚Ð¾ÐºÐµÐ½Ð¾Ð² Ð²ÐµÑÑŒ Ð²Ñ‹Ð²Ð¾Ð´ = final (reasoning_tokens=0). Commentary Ð¿Ð¾Ð´Ð´ÐµÑ€Ð¶Ð¸Ð²Ð°ÐµÑ‚ÑÑ ÐºÐ°Ðº Ð¿Ñ€Ð¾Ð·Ñ€Ð°Ñ‡Ð½Ñ‹Ð¹ ÐºÐ°Ð½Ð°Ð».

ReasoningPresetApplied emitted to internal eventbus when reasoning_preset supplied.

Notes:

- Session history stored in-memory (TTL 60m, max 50 msgs). Prompt is constructed with a sliding window (oldest messages dropped to respect model context and reserved output budget).
- prompt_tokens and context_used_* are approximate (whitespace split heuristic).
- decode_tps = output_tokens / (latency_ms/1000).

Test-mode aids (MIA_TEST_MODE=1 only):

- A lightweight `meta` SSE frame is emitted at the very start with
  `{ request_id, model_id, status }` to help tests obtain `request_id`
  deterministically before tokens.
- When dev overrides are provided, a small pre-stream delay may be applied to
  allow clients to wire cancellation before the first token.
Both behaviors are disabled in production (when `MIA_TEST_MODE` is not set).

### Stop Sequences

Configured via `llm.stop` (list of strings). On match:

- Truncates trailing matched sequence from final answer (after stream assembly safeguard).
- Emits `GenerationCompleted.stop_reason="stop_sequence"`.
- In Harmony mode stop sequences operate only on `final` channel output (analysis unaffected).


### Cancellation (Sprint 3B)

Endpoint (planned): `POST /cancel/{request_id}` â€” sets cancel token. Stream ends with `stop_reason="cancelled"` and partial output; Ð±ÑƒÐ´ÐµÑ‚ ÑÐ¾Ð±Ñ‹Ñ‚Ð¸Ðµ `GenerationCancelled` + Ð¼ÐµÑ‚Ñ€Ð¸ÐºÐ° `generation_cancelled_total{reason}`.

### Persona & Obsidian (Sprint 3C)

If enabled and persona file loaded: additional fields in `GenerationStarted`:
`app_persona_hash`, `app_persona_version`.

