# Config Registry

Реестр конфигурационных ключей. Источники (приоритет сверху вниз): ENV (MIA__*) → overrides.yaml → base.yaml → defaults.

| Key path | Type | Default | Module | Reloadable | Notes |
|----------|------|---------|--------|-----------|-------|
| schema_version | int | 1 | core | no | Версия агрегированной схемы (миграции) |
| modules.enabled[] | list[string] | derived | core | yes | Активные модули (управляется ModuleManager) |
| llm.primary.id | string | gpt-oss-20b-mxfp4 | llm | no | Primary baseline switched to MXFP4 (2025-08-24; prev q4km) |
| llm.primary.temperature | float | 0.7 | llm | yes | Диапазон 0–2 |
| llm.primary.top_p | float | 0.9 | llm | yes | 0–1 |
| llm.primary.max_output_tokens | int | 1024 | llm | yes | Ограничение вывода |
| llm.primary.n_gpu_layers | int | auto | llm | no | Авто распределение на GPU |
| llm.primary.n_threads | int? | null | llm | yes | Кол-во потоков CPU (None → llama.cpp default) |
| llm.primary.n_batch | int? | null | llm | yes | Batch size для context / eval (None → llama.cpp default) |
| llm.lightweight.id | string | phi-3.5-mini-instruct-q4_0 | llm | no | Быстрый режим |
| llm.lightweight.temperature | float | 0.4 | llm | yes | |
| llm.optional_models.* | map | — | llm | yes | В текущей версии пусто (gpt-oss перенесён в primary) |
| llm.skip_checksum | bool | false | llm | no | Для dev среды |
| llm.load_timeout_ms | int | 15000 | llm | no | Ожидание загрузки файла |
| llm.reasoning_presets.* | map | {low:{temperature:0.6,top_p:0.9}, medium:{...}} | llm | yes | Переопределения параметров генерации по режиму |
| embeddings.main.id | string | bge-m3 | embeddings | no | |
| embeddings.fallback.id | string | gte-small | embeddings | no | |
| rag.collection_default | string | memory | rag | no | DEFAULT_COLLECTION |
| rag.top_k | int | 8 | rag | yes | Кол-во документов |
| rag.hybrid.weight_semantic | float | 0.6 | rag | yes | Вес dense |
| rag.hybrid.weight_bm25 | float | 0.4 | rag | yes | Вес sparse |
| rag.normalize.min_score | float | 0.0 | rag | yes | Нормализация |
| rag.normalize.max_score | float | 1.0 | rag | yes | |
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

S1 Migration:

1. Если legacy `base.yaml` не содержит `schema_version` → автоматически добавляется `1` (лог предупреждения).
2. Если отсутствует `modules` → формируется `modules.enabled` из присутствующих корневых ключей (`llm`, `embeddings`, `rag`, `emotion`, `reflection`, `metrics`, `logging`, `storage`, `system`, `perf`).
3. Поведение и значения под‑схем не меняются; валидация по прежнему строгая (неизвестные ключи внутри namespace → ошибка).

Примечания:

1. Reloadable — можно применять без рестарта (горячая перезагрузка части модулей).
2. Изменение не reloadable ключей требует перезапуска процесса.
3. Валидация: неизвестный ключ → ошибка загрузки.

