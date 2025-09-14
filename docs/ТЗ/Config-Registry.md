# Config Registry

Реестр конфигурационных ключей. Источники (приоритет сверху вниз): ENV (MIA__*) → overrides.yaml → base.yaml → defaults.

| Key path | Type | Default | Module | Reloadable | Notes |
|----------|------|---------|--------|-----------|-------|
| schema_version | int | 1 | core | no | Версия агрегированной схемы (миграции) |
| modules.enabled[] | list[string] | derived | core | yes | Активные модули (управляется ModuleManager) |
| llm.primary.id | string | gpt-oss-20b-mxfp4 | llm | no | Primary baseline (паспорт: [gpt-oss-20b-mxfp4](passports/gpt-oss-20b-mxfp4.md)) |
| llm.primary.temperature | float | 0.7 | llm | yes | Диапазон 0–2 |
| llm.primary.top_p | float | 0.9 | llm | yes | 0–1 |
| llm.primary.top_k | int | 40 | llm | yes | >0 |
| llm.primary.repeat_penalty | float | 1.1 | llm | yes | 0.5–2.5 |
| llm.primary.min_p | float | 0.05 | llm | yes | 0–1 |
| llm.primary.max_output_tokens | int | 1024 | llm | yes | Ограничение вывода |
| llm.primary.n_gpu_layers | int | auto | llm | no | Авто распределение на GPU |
| llm.primary.n_threads | int? | null | llm | yes | Кол-во потоков CPU (None → llama.cpp default) |
| llm.primary.n_batch | int? | null | llm | yes | Batch size для context / eval (None → llama.cpp default) |
| llm.lightweight.id | string | phi-3.5-mini-instruct-q3_k_s | llm | no | Lightweight (паспорт: [phi-3.5-mini-instruct-q3_k_s](passports/phi-3.5-mini-instruct-q3_k_s.md)) |
| llm.lightweight.temperature | float | 0.4 | llm | yes | Температура lightweight |
| llm.system_prompt.version | int | 1 | llm | no | Версия базового системного промпта |
| llm.system_prompt.allow_user_override | bool | false | llm | yes | Разрешить полную замену base prompt пользователем |
| llm.system_prompt.max_persona_chars | int | 1200 | llm | yes | Лимит длины persona слоя |
| llm.system_prompt.text | string | (short) | llm | no | Базовый системный промпт (Layer 1) |
| llm.optional_models.* | map | — | llm | yes | Доп. модели (judge alias, experimental) |
| llm.heavy_model_vram_threshold_gb | float | 10.0 | llm | yes | Порог размера (GiB) для auto-unload heavy |
| llm.generation_timeout_s | int | 120 | llm | no | Ограничение времени генерации (stream hard stop) |
| llm.fake | bool | false | llm | yes | Использовать DummyProvider для gguf (dev/tests) |
| llm.skip_checksum | bool | false | llm | no | Для dev среды |
| llm.load_timeout_ms | int | 15000 | llm | no | Ожидание загрузки файла |
| llm.reasoning_presets.* | map | {low:{temperature:0.6,top_p:0.9,reasoning_max_tokens:128}, ...} | llm | yes | Переопределения параметров + per-mode `reasoning_max_tokens` (low=128, medium=256, high=512) |
| llm.postproc.enabled | bool | true | llm | yes | Включить постпроцессинг (split reasoning/final) |
| llm.postproc.reasoning.max_tokens | int | 256 | llm | yes | Лимит reasoning токенов (обрезка + маркер) |
| llm.postproc.reasoning.drop_from_history | bool | true | llm | yes | Не сохранять reasoning в session history |
| llm.postproc.reasoning.ratio_alert_threshold | float | 0.45 | llm | yes | Порог доли reasoning к финальному ответу (alert metric) |
| llm.postproc.ngram.n | int | 3 | llm | yes | N для подавления мгновенных повторов |
| llm.postproc.ngram.window | int | 128 | llm | yes | Окно токенов для n-gram буфера |
| llm.postproc.collapse.whitespace | bool | true | llm | yes | Схлопывать повторяющиеся пробелы/переносы |
| llm.prompt.harmony.enabled | bool | true | llm | yes | Всегда включено (полная миграция на Harmony) |
| llm.stop[] | list[string] | [] | llm | yes | Stop sequences (обрезка вывода, stop_reason=stop_sequence) |
| llm.prompt.harmony.force | bool | true | llm | yes | Закреплено: единственный адаптер |
| llm.prompt.harmony.tags.analysis | string | analysis | llm | no | Тег начала reasoning канала |
| llm.prompt.harmony.tags.final | string | final | llm | no | Тег начала финального ответа |
| llm.commentary_retention.mode | string | metrics_only | llm | yes | Политика хранения: metrics_only\, hashed_slice\, redacted_snippets\, raw_ephemeral |
| llm.commentary_retention.hashed_slice.max_chars | int | 160 | llm | yes | Кол-во первых символов для хеша (SHA-256 → hex16) |
| llm.commentary_retention.redacted_snippets.max_tokens | int | 40 | llm | yes | Токены предпросмотра (редактируемые) |
| llm.commentary_retention.redacted_snippets.redact_pattern | string | (?i)(user\|secret\|api[_-]?key) | llm | yes | Regex маска чувствительных слов |
| llm.commentary_retention.redacted_snippets.replacement | string | *** | llm | yes | Подстановка вместо совпадений |
| llm.commentary_retention.raw_ephemeral.ttl_seconds | int | 300 | llm | yes | TTL секунд для эфемерного хранения |
| llm.commentary_retention.store_to_history | bool | false | llm | yes | True → commentary попадёт в history |
| llm.commentary_retention.tool_chain.detect | bool | true | llm | yes | Детектировать tool commentary префикс `[tool:...]` |
| llm.commentary_retention.tool_chain.apply_when | string | raw_ephemeral | llm | yes | raw_ephemeral\|hashed_slice\|redacted_snippets\|any |
| llm.commentary_retention.tool_chain.override_mode | string | hashed_slice | llm | yes | hashed_slice\|redacted_snippets (режим после override) |
| llm.commentary_retention.tool_chain.tag_in_summary | bool | true | llm | yes | Добавлять original_mode→override тег в summary |
| llm.tool_calling.enabled | bool | true | llm | yes | Включить парсинг tool channel |
| llm.tool_calling.max_payload_bytes | int | 8192 | llm | yes | Лимит размера JSON payload инструмента |
| llm.tool_calling.retention.mode | string | metrics_only | llm | yes | metrics_only\|hashed_slice\|redacted_snippets\|raw_ephemeral |
| llm.tool_calling.retention.hash_preview_max_chars | int | 200 | llm | yes | Обрезка перед хешированием аргументов |
| llm.tool_calling.retention.redacted_placeholder | string | [REDACTED] | llm | yes | Подстановка для режима redacted_snippets |
| embeddings.main.id | string | bge-m3 | embeddings | no | |
| embeddings.fallback.id | string | gte-small | embeddings | no | |
| rag.collection_default | string | memory | rag | no | DEFAULT_COLLECTION |
| rag.enabled | bool | true | rag | yes | Master switch; false → отключает retrieval |
| rag.top_k | int | 8 | rag | yes | Кол-во документов |
| rag.hybrid.weight_semantic | float | 0.6 | rag | yes | Вес dense |
| rag.hybrid.weight_bm25 | float | 0.4 | rag | yes | Вес sparse |
| rag.normalize.method | string | minmax | rag | yes | minmax\|zscore (см. ADR-0032) |
| rag.normalize.epsilon | float | 1e-6 | rag | yes | Защита от деления на 0 (min-max) |
| rag.normalize.min_score | float | 0.0 | rag | yes | Нормализация |
| rag.normalize.max_score | float | 1.0 | rag | yes | |
| rag.context.max_fraction_of_window | float | 0.80 | rag | yes | Доля окна контекста под RAG вставку |
| rag.expansion.enabled | bool | false | rag | yes | Включить QueryExpander |
| rag.expansion.model | string | lightweight | rag | yes | Модель для expansion (идентификатор из llm/lightweight) |
| emotion.model.id | string | distilroberta-multilingual-emotion | emotion | no | |
| emotion.fsm.hysteresis_ms | int | 2000 | emotion | yes | Минимум между сменами |
| reflection.enabled | bool | true | reflection | yes | Ночной цикл |
| reflection.schedule.cron | string | `0 3 * * *` | reflection | yes | 03:00 локальное |
| reflection.triggers.token_threshold | int | 8000 | reflection | yes | On-demand trigger (messages tokens) |
| reflection.triggers.idle_seconds | int | 7200 | reflection | yes | On-demand trigger (2h idle) |
| metrics.export.prometheus_port | int | 9090 | metrics | no | Порт экспорта |
| logging.level | string | info | core | yes | debug/info/warn/error |
| logging.format | string | json | core | no | json\|text |
| storage.paths.models | string | models | storage | no | Базовый путь моделей |
| storage.paths.cache | string | .cache | storage | no | |
| storage.paths.data | string | data | storage | no | |
| system.locale | string | ru-RU | core | yes | Языковые настройки |
| system.timezone | string | Europe/Moscow | core | no | |
| prompt.context.min_last_messages | int | 6 | prompt | yes | Минимум сообщений истории |
| prompt.context.fraction | float | 0.30 | prompt | yes | Доля окна под историю |
| session.title.auto_generate | bool | true | session | yes | Генерация после первого user сообщения |
| attachments.embed.auto_threshold_mb | int | 10 | attachments | yes | Auto-ingest size threshold |
| attachments.embed.on_upload | bool | true | attachments | yes | Авто запуск индексации (<= threshold) |
| permissions.auto_prompt | bool | true | permissions | yes | UI диалог при запросе |
| permissions.allowed_roots[] | list[string] | ["."] | permissions | yes | Sandbox корни |
| persona.reminder_interval | int | 8 | persona | yes | Через сколько сообщений повторять persona_block |
| speech.enabled | bool | false | speech | yes | Включение TTS |
| speech.default_voice | string | mia_default | speech | yes | Базовый голос |
| speech.sample_rate_hz | int | 22050 | speech | no | Аудио формат v1 |
| speech.cache_ttl_sec | int | 86400 | speech | yes | TTL аудио кэша |
| speech.p95_latency_target_ms | int | 500 | speech | yes | Цель p95 |
| speech.p95_latency_max_ms | int | 800 | speech | yes | Порог деградации |
| media.generation.enabled | bool | false | media | yes | Включение image/video |
| media.image.provider | string | stub | media | yes | Провайдер изображений |
| media.video.provider | string | stub | media | yes | Провайдер видео |
| media.max_image_resolution | int | 1048576 | media | yes | Пиксели (W*H) максимум |
| media.max_video_duration_s | int | 10 | media | yes | Длительность ролика |
| media.cache.max_mb | int | 512 | media | yes | Лимит диска кэша |
| perf.thresholds.tps_regression_pct | float | 0.12 | perf | yes | Допустимое относительное падение tokens_per_s (12%) (MXFP4 baseline) |
| perf.thresholds.p95_regression_pct | float | 0.18 | perf | yes | Допустимый относительный рост p95 decode latency short (18%) |
| perf.thresholds.p95_ratio_limit | float | 1.30 | perf | yes | SLA: верхняя граница p95_long / p95_short |
| perf.thresholds.p95_ratio_regression_pct | float | 0.20 | perf | yes | Допустимый относительный рост p95_ratio vs предыдущего отчёта (20%) |
| observability.metrics.enabled | bool | true | observability | yes | Экспорт метрик |
| observability.metrics.port | int | 9090 | observability | no | HTTP порт |
| observability.logging.level | string | info | observability | yes | Уровень логов модуля |
| observability.tracing.enabled | bool | false | observability | yes | Корреляция/трейс контекст |

Автоген снапшот схем: см. [`Generated-Config.md`](Generated-Config.md) (обновляется скриптом `scripts/generate_config_docs.py`, тест `test_generated_config_docs_up_to_date`). Manual registry (этот файл) остаётся источником более богатых пояснений.

Harmony Channels (полная миграция):

- Инкрементальный парсер Harmony извлекает каналы `analysis` и `final`.
- Legacy marker режим и ключи (`final_marker`, fallback *) удалены.
- Если спец‑токены не обнаружены (неадаптированная модель) — весь вывод трактуется как `final` (reasoning_tokens=0) без попытки маркерного fallback.
- `drop_from_history` всегда исключает `analysis` из истории (final сохраняется).
- Метрики: reasoning_tokens, final_tokens, reasoning_ratio — единая семантика.

S1 Migration:

1. Если legacy `base.yaml` не содержит `schema_version` → автоматически добавляется `1` (лог предупреждения).
2. Если отсутствует `modules` → формируется `modules.enabled` из присутствующих корневых ключей (`llm`, `embeddings`, `rag`, `emotion`, `reflection`, `metrics`, `logging`, `storage`, `system`, `perf`).
3. Поведение и значения под‑схем не меняются; валидация по прежнему строгая (неизвестные ключи внутри namespace → ошибка).

Примечания:

1. Reloadable — можно применять без рестарта (горячая перезагрузка части модулей).
2. Изменение не reloadable ключей требует перезапуска процесса.
3. Валидация: неизвестный ключ → ошибка загрузки.

