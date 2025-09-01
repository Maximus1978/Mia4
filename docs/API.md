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

Response: `{ "ui_mode": "admin"|"user" }`

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

Response: `Content-Type: text/event-stream` frames:

- `event: token` data: `{ seq:int, text:str, tokens_out:int, request_id, model_id }`
- `event: reasoning` (optional; only if postproc.reasoning.drop_from_history = false and reasoning produced)
  data: `{ request_id, model_id, reasoning:str }` (full buffered chain-of-thought up to marker)
- `event: usage` data: `{ request_id, model_id, prompt_tokens:int, output_tokens:int, latency_ms:int, decode_tps:float, reasoning_tokens:int?, final_tokens:int?, reasoning_ratio:float? }`
- `event: error` data: `{ request_id, model_id, code, error_type, message }` (UI displays `code`)
- `event: end` data: `{ request_id, status:"ok"|"error" }`

Planned (Sprint 3A/3B extensions):

- `event: analysis` (Harmony Stage 2) data: `{ request_id, text, seq }` (reasoning channel) — optional.


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

Reasoning-specific behavior:

- Split performed by marker (default `===FINAL===`). Text before marker treated as reasoning, withheld from token stream (buffered) and optionally emitted as separate `reasoning` event.
- If marker absent, all output treated as final answer (reasoning_tokens=0 fallback).
- `reasoning_tokens` counts whitespace-split tokens prior to marker capped by `postproc.reasoning.max_tokens`.
- Reasoning presets can override this cap via per-preset key `reasoning_max_tokens` (low/medium/high example: 128/256/512). Applied server-side each request.
- If `drop_from_history=true` (default) reasoning is never sent to client nor stored; only aggregate counts appear in `usage`.
- Metric `reasoning_buffer_latency_ms` (Prometheus) records delay between final marker detection and stream completion.

Harmony tag mode (experimental):

- Enable via `llm.prompt.harmony.enabled=true`.
- Model expected to emit `<analysis>...</analysis><final>...</final>` (tag names configurable in config registry).
- Stage 1 implementation buffers full output, then streams only `<final>` content as token events (no separate `reasoning` SSE yet).
- If tags missing → fallback to marker behavior described above.
- `drop_from_history` suppression currently applies only to marker mode (policy for Harmony pending) — reasoning text may still appear in final stats event; do not persist it client-side.
- Future Stage 2: incremental streaming + dedicated `analysis` SSE channel, then removal of need for `===FINAL===` marker.

ReasoningPresetApplied emitted to internal eventbus when reasoning_preset supplied.

Notes:

- Session history stored in-memory (TTL 60m, max 50 msgs).
- prompt_tokens is approximate (whitespace split placeholder).
- decode_tps = output_tokens / (latency_ms/1000).

### Stop Sequences

Configured via `llm.stop` (list of strings). On match:

- Truncates trailing matched sequence from final answer.
- Emits `GenerationCompleted.stop_reason="stop_sequence"`.
- Marker `===FINAL===` retained as fallback until Harmony Stage 2 stable.


### Cancellation (Sprint 3B)

Endpoint (proposed): `POST /cancel/{request_id}` — sets cancel token. Stream ends with `stop_reason="cancelled"` and partial output.

### Persona & Obsidian (Sprint 3C)

If enabled and persona file loaded: additional fields in `GenerationStarted`:
`app_persona_hash`, `app_persona_version`.
