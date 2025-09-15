# MIA4 API (Phase 2 MVP)

Endpoints

Cross-links:

- Events contract: `ТЗ/Events.md`
- Config registry (sampling, postproc keys): `ТЗ/Config-Registry.md`
- Model passports details: `ТЗ/passports/`
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

- `event: token` data: `{ seq:int, text:str, tokens_out:int, request_id, model_id }` (final channel user‑visible deltas)
- `event: analysis` data: `{ request_id, model_id, text:str }` (Harmony reasoning channel; NOT persisted; may be suppressed in minimal mode)
- `event: usage` data: `{ request_id, model_id, prompt_tokens:int, output_tokens:int, latency_ms:int, decode_tps:float, context_used_tokens:int?, context_total_tokens:int?, context_used_pct:float?, reasoning_tokens:int?, final_tokens:int?, reasoning_ratio:float? }`
- `event: error` data: `{ request_id, model_id, code, error_type, message }`
- `event: end` data: `{ request_id, status:"ok"|"error" }`

Tool calling (Harmony tool channel):

- `event: commentary` may include a JSON stringified tool result payload (synthetic for MVP) with shape `{tool, status, ok, error_type?, message?, preview_hash?, args_redacted?, raw_args?}` depending on retention mode.
- Internal events (not SSE) emitted on bus: `ToolCallPlanned{request_id,tool,args_preview_hash,seq}` then `ToolCallResult{request_id,tool,status,latency_ms,seq,error_type?,message?}`.
- Payload size limit configurable: `llm.tool_calling.max_payload_bytes` (default 8192). Oversize → `status=error`, `error_type=tool_payload_too_large`.
- Malformed JSON → `status=error`, `error_type=tool_payload_parse_error`.
- Retention modes (`llm.tool_calling.retention.mode`):
  - `metrics_only` (no tool result body beyond status commentary line)
  - `hashed_slice` (includes `preview_hash`)
  - `redacted_snippets` (hash + `args_redacted` placeholder)
  - `raw_ephemeral` (hash + trimmed raw args – debug only)

Final token accounting guarantee:
Adapter flushes any undispatched final deltas on `finalize()` so `final_tokens == count(token events)` always holds.

Legacy / conditional:

- `event: reasoning` (legacy marker mode only; buffered full reasoning text when `drop_from_history=false`). New Harmony path uses streaming `analysis` events instead.


Sampling metadata:

В событиях `GenerationStarted` и `GenerationCompleted.result_summary.sampling` присутствует объект:

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

Поле `filtered_out` (если не пусто) показывает какие переданные клиентом параметры были отброшены текущей версией `llama_cpp` (не поддерживаются её сигнатурой). Это помогает диагностировать несоответствие настроек.

Sampling origins (Sprint 3A):

`GenerationStarted.sampling_origin` (and per-field annotation) shows source precedence: `passport` < `preset` < `custom`.

Merged sampling object (`GenerationStarted.sampling`) also carries `filtered_out` plus explicit `max_tokens` (alias of effective `max_output_tokens`) and is mirrored in `GenerationCompleted.result_summary.sampling`.

Reasoning & Harmony channels (единственный режим):

- Model emits structured channel tokens (Harmony format) internally; adapter extracts `analysis` vs `final`.
- `analysis` deltas stream as separate SSE events and are excluded from session history regardless of `drop_from_history`.
- `commentary` (pass-through, не считаются в reasoning/final токены) может появляться для пользовательских преамбул (action plan) и отображается как `event: commentary`.
- `reasoning_tokens` counts whitespace‑split analysis tokens up to `postproc.reasoning.max_tokens` (or preset override `reasoning_max_tokens`).
- `final_tokens` counts user‑visible tokens (token events).
- `reasoning_ratio = reasoning_tokens / (reasoning_tokens + final_tokens)` (0 if denominator 0).
- Alert threshold configured via `llm.postproc.reasoning.ratio_alert_threshold`; crossings increment alert metric.
- Metric `reasoning_buffer_latency_ms` retained (legacy—may read 0 when no buffering occurred).

Legacy marker режим удалён; при отсутствии Harmony спец‑токенов весь вывод = final (reasoning_tokens=0). Commentary поддерживается как прозрачный канал.

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

Endpoint (planned): `POST /cancel/{request_id}` — sets cancel token. Stream ends with `stop_reason="cancelled"` and partial output; будет событие `GenerationCancelled` + метрика `generation_cancelled_total{reason}`.

### Persona & Obsidian (Sprint 3C)

If enabled and persona file loaded: additional fields in `GenerationStarted`:
`app_persona_hash`, `app_persona_version`.
