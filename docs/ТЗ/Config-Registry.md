# Config Registry

Реестр конфигурационных ключей. Источники (приоритет сверху вниз): ENV (MIA__*) → overrides.yaml → base.yaml → defaults.

| Key path | Type | Default | Module | Reloadable | Notes |
|----------|------|---------|--------|-----------|-------|
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
| metrics.export.prometheus_port | int | 9090 | metrics | no | Порт экспорта |
| logging.level | string | info | core | yes | debug/info/warn/error |
| logging.format | string | json | core | no | json\|text |
| storage.paths.models | string | models | storage | no | Базовый путь моделей |
| storage.paths.cache | string | .cache | storage | no | |
| storage.paths.data | string | data | storage | no | |
| system.locale | string | ru-RU | core | yes | Языковые настройки |
| system.timezone | string | Europe/Moscow | core | no | |
| perf.thresholds.tps_regression_pct | float | 0.12 | perf | yes | Допустимое относительное падение tokens_per_s (12%) (MXFP4 baseline) |
| perf.thresholds.p95_regression_pct | float | 0.18 | perf | yes | Допустимый относительный рост p95 decode latency short (18%) |
| perf.thresholds.p95_ratio_limit | float | 1.30 | perf | yes | SLA: верхняя граница p95_long / p95_short |
| perf.thresholds.p95_ratio_regression_pct | float | 0.20 | perf | yes | Допустимый относительный рост p95_ratio vs предыдущего отчёта (20%) |

Примечания:

1. Reloadable — можно применять без рестарта (горячая перезагрузка части модулей).
2. Изменение не reloadable ключей требует перезапуска процесса.
3. Валидация: неизвестный ключ → ошибка загрузки.

