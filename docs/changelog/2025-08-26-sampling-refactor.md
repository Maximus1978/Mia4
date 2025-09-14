# 2025-08-26 – Sampling & Provider Refactor

## Summary

Расширен и нормализован контроль параметров генерации и повышена устойчивость `/generate`.

## Key Changes

- Added full set of sampling overrides (top_k, repeat_penalty, min_p, typical_p, presence_penalty, frequency_penalty, repeat_last_n, penalize_nl, seed, mirostat, mirostat_tau, mirostat_eta) to overrides pipeline.
- Extended `GenerateOverrides` schema (API route) – теперь все параметры проходят до провайдера.
- Injected sampling metadata (включая max_tokens) в события `GenerationStarted` и `GenerationCompleted`.
- Removed TypeError fallback double-call: введён единый предвательный фильтр по сигнатуре `llama.__call__`.
- Added `filtered_out` list в sampling метаданные (видно какие параметры были отброшены версией llama.cpp).
- Unified pass-through of `max_output_tokens` → `max_tokens`.
- Cleaned indentation / corruption в `llama_cpp_provider.py` (предыдущие артефакты сломанных блоков устранены).
- Ensured fake streaming tests still pass (5 tests green) после рефактора.

## Rationale

Цель — приблизить стиль ответов к ожидаемому (как в LM Studio) за счёт точного контроля sampling и прозрачности того, какие параметры реально применены. Фильтрация вместо fallback сокращает скрытые ошибки и исключает двойной запуск.

## Observability

- Sampling параметры теперь эмитятся в начале и конце с полем `filtered_out`.
- Это облегчит диагностику 500 ошибок (можно увидеть, были ли ключевые параметры отброшены).

## Known Issues (Open)

- HTTP 500 при реальной генерации остаётся (нет traceback). Требуется внедрить structured logging в маршруте `/generate`.
- Возможна двойная эмиссия `GenerationStarted` (маршрут + провайдер) — нужно унифицировать источник.
- Нет тестов на advanced params propagation / filtered_out.
- Документация (Config-Registry / API.md) ещё не отражает новые override поля.

## Next Steps

1. Добавить try/except + JSON error body в `/generate` до старта SSE.
2. Поверх событий — surfacing `filtered_out` в UI (отладочный tooltip).
3. Добавить feature-flag тест real model (skip by default) для раннего обнаружения 500.
4. Обновить `API.md` и конфиг реестр.

## Risk

Пока 500 не устранён — влияние новых sampling настроек на реальную модель не подтверждено.

--- end --
