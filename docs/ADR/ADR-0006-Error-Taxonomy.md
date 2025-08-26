# ADR-0006: Error Taxonomy

Status: Accepted (2025-08-25)

## Контекст

Единый набор `error_type` значений нужен для событий (GenerationFailed, ModelLoadFailed, Permission.Requested/Denied future), для унифицированных метрик и регрессий. Разрозненные строки усложняют фильтрацию и тесты.

## Решение

Вводим фиксированный enum (строки kebab-case). Расширение только через PR + обновление этого ADR.

Группы:

| Category | Codes | Notes |
|----------|-------|-------|
| model.load | file-not-found, checksum-mismatch, incompatible-format, init-timeout, provider-internal | ModelLoadFailed |
| generation.request | invalid-params, context-overflow, safety-filtered | До запуска ядра провайдера |
| generation.runtime | provider-error, oom, timeout, aborted, stream-broken | GenerationCompleted(status=error) |
| permissions | scope-denied, scope-timeout | (Denied event future) |
| rag | retriever-error, ranker-error | RAG.* (future) |
| memory | write-failed, read-failed | Memory.* (future) |
| reflection | pipeline-error | Reflection.* |
| media.speech | tts-internal, tts-timeout, tts-cache-error | Speech.* |
| media.gen | media-internal, media-timeout | Media.Generated (future error variant) |
| config.validation | config-out-of-range, config-invalid | Нарушение правил валидации / нормализации конфигурации (loader) |

Правило: код отражает техническую причину (не пользовательский текст). Дополнительная детализация помещается в поле `message` (не парсится логикой метрик).

## Эволюция

MINOR: добавление нового кода (backward compatible) → обновить таблицу.
MAJOR: переименование кода → вводится новый, старый остаётся deprecated ≥1 релиз.

## Валидация

Тест `test_error_codes_enum.py` сверяет набор констант с таблицей (генератор списка из этого файла парсить не будем — дублируем в test для явности).

## Последствия

- Плюсы: стабильные дешевые фильтры, регрессионные алерты, отсутствие «орфографических» расхождений.
- Минусы: добавление кода требует ревью ADR.

## Связанные

- Events.md (колонка error_type)
- Perf.md (регрессии по generation.runtime)
