# Events

Список внутренних событий (канонический контракт). Поля сериализуются в structured log + внутреннюю шину.

| EventName | Required Fields | Optional Fields | Emitter | Consumers | Notes | Version |
|-----------|-----------------|-----------------|---------|-----------|-------|---------|
| ModelLoaded | model_id, role, load_ms, revision | reasoning_modes | ModelRegistry | Metrics, Orchestrator | После успешной загрузки модели | 1 |
| ModelUnloaded | model_id, role, reason | idle_seconds | ModelRegistry | Metrics | Выгрузка по idle или ручная | 1 |
| ModelLoadFailed | model_id, role, error_type | message, retry_in_ms | ModelRegistry | Alerting, Orchestrator | Ошибка чтения / checksum / init | 1 |
| GenerationStarted | request_id, model_id, role, prompt_tokens | system_prompt_version, system_prompt_hash, persona_len, parent_request_id, correlation_id, sampling (incl. merged_sampling\, sampling_origin\, stop_sequences) | LLMProvider | Metrics, Tracing | Начало генерации (sampling включает применённые параметры + max_tokens + filtered_out; sampling_origin=passport\|preset\|user\|mixed) | 2 |
| GenerationChunk | request_id, model_id, role, seq, text, tokens_out | correlation_id | LLMProvider | StreamingConsumers | Стриминговый кусок вывода | 2 |
| GenerationCompleted | request_id, model_id, role, status, output_tokens, latency_ms | stop_reason, error_type, message, correlation_id, result_summary (incl. sampling_origin\, merged_sampling) | LLMProvider | Metrics, Memory | Терминальное событие; result_summary.sampling зеркалирует GenerationStarted.sampling; stop_reason=stub\|eos\|error\|stop_sequence | 2 |
| ChecksumMismatch | model_id, expected, actual | path | ModelRegistry | Alerting | Блокирующая ошибка | 1 |
| JudgeInvocation | request_id, model_id, target_request_id | agreement | Eval | Metrics | Вызов судьи (MoE) | 1 |
| PlanGenerated | request_id, steps_count | model_id | Planner | AgentLoop | План задач | 1 |
| ReasoningPresetApplied | request_id, preset, mode | temperature, top_p, overridden_fields | Orchestrатор | Metrics | Применён reasoning пресет (mode baseline/overridden; overridden_fields изменённые ключи) | 2 |
| Session.Created | session_id, workspace_id | title | SessionService | UI, Memory | Создана новая сессия | 1 |
| Session.TitleUpdated | session_id, title, auto | workspace_id | SessionService | UI | Обновлён заголовок | 1 |
| Message.Appended | message_id, session_id, workspace_id, role | token_counts | SessionService | Memory, RAG | Сообщение добавлено | 1 |
| Attachment.Stored | attachment_id, session_id, workspace_id, mime, size | hash | AttachmentService | IngestWorker | Файл сохранён | 1 |
| Ingest.Requested | attachment_id, embed_model | workspace_id | AttachmentService | IngestWorker | Индексация запрошена | 1 |
| RAG.QueryRequested | request_id, query, user_id | expansion_planned, strategies[], top_k | RAG | Orchestrator | Запрос RAG инициализирован | 1 |
| RAG.ResultsReady | request_id, items[], latency_ms | top_k | RAG | Orchestrator | Результаты retrieval | 1 |
| RAG.IndexRebuilt | count, duration_ms | collection | RAG | Metrics | Полная перестройка индекса | 1 |
| WakeWord.Detected | ts, confidence, phrase | device_id | SensorService | AgentLoop | Активация голосом | 1 |
| Tone.Classified | message_id, tone_label, confidence | model_id | EmotionAnalyzer | PreferenceEngine | Классификация тона | 1 |
| Preference.Updated | user_id, changed_fields[] | traits_delta | PreferenceEngine | UI | Обновлены предпочтения | 1 |
| Reflection.RunStarted | run_id, started_ts | trigger | ReflectionScheduler | Metrics | Начало рефлексии | 1 |
| Reflection.RunFinished | run_id, duration_ms, insights_count | trigger | ReflectionScheduler | Memory, Metrics | Завершение рефлексии | 1 |
| Recommendation.Generated | session_id, rec_type, target_ids[] | score | Recommender | UI | Рекомендация готова | 1 |
| Permission.Requested | scope, requested_ts | reason | ToolAccess | UI | Запрос прав | 1 |
| Permission.Granted | scope, granted_ts | ttl_sec, constraints | ToolAccess | All | Выдан доступ | 1 |
| Agent.TriggerFired | trigger_id, action | correlation_id | AgentLoop | Orchestrator | Сработал триггер | 1 |
| Speech.Requested | request_id, text_len, voice_id | correlation_id | SpeechService | Metrics | Запрошен синтез | 1 |
| Speech.Synthesized | request_id, duration_ms, audio_ms, voice_id | cache_hit | SpeechService | UI, Metrics | Аудио готово | 1 |
| Media.Generated | media_id, media_type, model_id, latency_ms | resolution, duration_ms | MediaService | UI | Медиа готово | 1 |
| Camera.FrameCaptured | media_id, resolution | device_id | SensorService | MediaService | Кадр камеры | 1 |
| Camera.ClipCaptured | media_id, duration_ms, resolution | device_id | SensorService | MediaService | Видеоклип камеры | 1 |
| ToolCallPlanned | request_id, tool, args_preview_hash, seq | args_schema_version | Route (Harmony adapter) | Metrics | Планируемый вызов инструмента (аргументы хэшированы) | 1 |
| ToolCallResult | request_id, tool, status, latency_ms, seq | error_type, message | Route (Harmony adapter) | Metrics | Результат синтетического (MVP) вызова | 1 |

Правила:

1. `request_id` глобально уникален.
2. События Generation* не эмитятся для zero-shot embed операций.
3. При ошибке загрузки ретрай по экспоненциальной схеме вне этого контракта.
4. JudgeInvocation и PlanGenerated могут следовать за GenerationCompleted для тех же моделей (разделение обязанностей уровня orchestration).
5. ReasoningPresetApplied фиксирует выбор профиля до генерации.

Cross-links:

- API SSE contract: `../API.md#post-generate-sse`
- Config registry: `Config-Registry.md` (llm.postproc.*, llm.reasoning_presets.*, llm.stop)
- ADR: ADR-0012 (GenerationResult), ADR-0015 (Model Fallback & Stub), ADR-0016 (Model Passports)
- Postproc & leakage remediation: ADR-0014 (hotfix 2025-09-01)

## Derived Metrics Mapping (Generation / Postproc)

| Metric | Source Event / Stage | Labels | Purpose | Notes |
|--------|----------------------|--------|---------|-------|
| generation_first_token_latency_ms | First token emission (SSE) | model | UX latency p50/p95 | Observed on first token frame |
| generation_latency_ms | GenerationCompleted | model | Total wall latency | Includes reasoning buffer time |
| generation_decode_tps | Route post-completion | model | Throughput (tokens/s) | Derived (tokens/seconds) |
| reasoning_buffer_latency_ms | Postproc finalization | model | Buffer overhead | 0 when no reasoning or no buffer |
| reasoning_ratio_alert_total | Route helper | model, bucket | Governance (excess reasoning) | bucket=above/below threshold |
| reasoning_leak_total | Postproc heuristic (legacy marker) | mode | Safety: unintended leak detection | legacy only (Harmony full) |
| tool_calls_total | ToolCallResult | tool\+status | Usage frequency / errors | status=ok\|error |
| tool_call_latency_ms | ToolCallResult | tool | Perf distribution | synthetic MVP near-zero |
| sse_stream_open_total | Route entry | model | Traffic | Increments at stream start |
| sse_stream_close_total | Route end | model, reason | Traffic / reliability | reason=ok/error |
| model_provider_reuse_total | Model registry (alias) | model | Alias reuse observability | Increments when alias attached |

Absence of `reasoning_leak_total` counter in snapshot implies zero detected leaks so far.

## Пример лог-записи ReasoningPresetApplied

```json
{
	"event": "ReasoningPresetApplied",
	"request_id": "a1b2c3d4",
	"mode": "medium",
	"temperature": 0.7,
	"top_p": 0.92,
	"ts": 1734543453.123
}
```

Использование: агрегация метрик частоты режимов и сравнение latency/tokens_s по режимам.

## EventBus (Spec Draft)

EventBus v1 (sync, in-process): напрямую вызывает обработчики.

| Aspect | Правило |
|--------|--------|
| API | subscribe(event, handler), emit(event, payload) |
| Payload Base Fields | event, ts |
| Handler Failures | Перехватываются, логируются, не останавливают emit |
| Ordering | Не гарантируется между разными событиями, внутри одного emit — последовательный вызов подписчиков |
| Versioning | Таблица событий содержит столбец Version; изменение структуры → либо инкремент версии поля payload.v, либо новое событие |

Переход на v2 (async) добавит очередь и лимиты (events.queue.max). Конфиг появится после принятия ADR-0002.

## Payload Versioning

- События фиксируются с версией в таблице.
- Для эволюции без rename: добавляется поле `v` в payload (если нужно различать формы).
- BREAKING изменения требуют нового имени или явного раздела миграций.

## Error Handling Semantics

- GenerationCompleted.status = ok|error заменяет пару GenerationFinished / GenerationFailed.
- Ошибочные состояния всегда имеют класс ошибок (error_type) из фиксированного множества (ADR-0006).

## Publish / Subscribe Mapping (Draft)

| Module | Publishes | Subscribes |
|--------|-----------|------------|
| LLM | GenerationStarted, GenerationChunk, GenerationCompleted, ReasoningPresetApplied | (в будущем) RAG.ResultsReady |
| ModelRegistry | ModelLoaded, ModelUnloaded, ModelLoadFailed, ChecksumMismatch | - |
| PerfCollector (planned) | Performance.Degraded (future) | Generation*, Model* |
| Observability (planned) | - | Все |
| RAG (planned) | RAG.QueryRequested, RAG.ResultsReady, RAG.IndexRebuilt | Memory.ItemStored |
| Memory (planned) | Memory.ItemStored, Memory.InsightMerged | - |
| Evaluation (planned) | JudgeInvocation, Eval.* | GenerationCompleted |

## GenerationResult

См. ADR-0012 (GenerationResult Contract). Поле status и агрегированные usage/timings отражаются в `GenerationCompleted.result_summary`.

## Deprecations

- GenerationFinished (v1) и GenerationFailed (v1) помечены как deprecated и будут удалены после минимального grace периода. Используйте GenerationChunk / GenerationCompleted.

