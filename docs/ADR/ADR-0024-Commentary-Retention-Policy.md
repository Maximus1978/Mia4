# ADR-0024: Commentary Channel Retention & Privacy Policy

Status: Accepted
Date: 2025-09-03

## Контекст

В Harmony добавлен канал `commentary`, отделённый от `analysis` (внутреннее рассуждение) и `final` (пользовательский ответ). Нужна политика хранения:

- Минимизировать риск утечки внутренних переходных формулировок или чувствительных временных данных.
- Сохранить достаточный объём для отладки качества и UX (почему финал такой, sequence of thought markers, latency spikes).
- Соблюдать инвариант: reasoning / analysis не попадает в history при `drop_from_history=true`.
- Установить чёткие правила какая часть commentary может быть ретроспективно использована (RAG, тренировка, аналитика).

## Проблемы без политики

1. Слепое сохранение commentary → риск PII/секретов (модель могла развернуть приватное из prompt).
2. Полное удаление → теряется сигнал для наблюдаемости (degradation, hallucination debugging).
3. Несогласованность между окружениями (prod сохраняет, dev нет) → несравнимые метрики.

## Цели

1. Защитить приватность (минимизация хранения дословного commentary).
2. Сохранить агрегируемый сигнал (метрики плотности, длины, распределение токенов по фазам).
3. Возможность выборочно включать raw-снимок с TTL для расследования инцидентов.
4. Детализировать политику ретенции в конфиге как единственный источник.

## Область (scope)

Канал `commentary` — промежуточные пояснения, подсказки, структурные переходы, которые могут быть частично близки к финалу, но не обязаны быть показаны пользователю.

## Решение (MVP)

Вводим многоуровневую ретенцию:

- ALWAYS METRICS: считаем количество токенов commentary, долю относительно final, latency распределение.
- HASHED SLICE (опция): первые N символов (конфигурируемо) хэшируются SHA256 → используем для дедупликации шаблонов.
- REDACTED SNIPPETS (опция): сохраняем первые M токенов, пропуская явно помеченные маркеры (regex: "user|secret|api[_-]?key" → замена `***`).
- RAW EPHEMERAL (опция): полный текст в in-memory кэше с TTL (минуты) для живой отладки.
- DISABLED: только метрики (default production posture).

## Конфигурация

```yaml
commentary_retention:
  mode: metrics_only   # metrics_only | hashed_slice | redacted_snippets | raw_ephemeral
  hashed_slice:
    max_chars: 160
  redacted_snippets:
    max_tokens: 40
    redact_pattern: "(?i)(user|secret|api[_-]?key)"
    replacement: "***"
  raw_ephemeral:
    ttl_seconds: 300
  store_to_history: false  # commentary никогда не входит в пользовательскую переписку
```

`store_to_history=false` жёстко форсируем независимо от остальных полей.

## Алгоритм применения

1. По завершении генерации адаптер передаёт финальный собранный commentary блоб в retention слой.
2. Retention слой согласно `mode` возвращает структуру для события `GenerationCompleted.commentary_retention_summary`:
   - `mode`
   - `token_count`
   - `ratio_to_final`
   - (optional) `hash_prefix` (первые 8 hex)
   - (optional) `snippet_redacted`
   - (optional) `ephemeral_cached=true`
3. В хранилище постоянном (если нужно) сохраняются только поля summary (без сырых данных).

## События / Метрики

Новые метрики:

- `commentary_tokens_total{model}` — счётчик.
- `commentary_retention_mode_total{mode}` — распределение режимов.
- `commentary_retention_redactions_total` — количество срабатываний редактирования.

Событие (расширение `GenerationCompleted`): поле `commentary_retention_summary`.

## Альтернативы

1. Полная очистка (только token_count) — недостаток сигнала при инцидентах.
2. Полный raw storage — риск конфиденциальности / нагрузка.
3. Дифференциация по типу пользователя — усложняет модель безопасности (отложено).

## Обоснование

Ступенчатая модель даёт баланс между приватностью и наблюдаемостью, легко понижать уровень (runtime config) без миграций схемы.

## Последствия

### Положительные

- Control-plane регулировка без деплоя.
- Снижение риска утечки через постоянное хранилище.
- Возможность статистического анализа паттернов commentary (через хэши).

### Отрицательные

- Немного дополнительной логики в завершении генерации.
- Память под ephemeral TTL cache.

## Тестирование

- Unit: redaction regex (положительные/отрицательные кейсы).
- Unit: hashed_slice длина и устойчивость (одинаковый вход → одинаковый hash_prefix).
- Unit: ratio_to_final вычисление (деление на 0 при пустом final → 0.0 / safe guard).
- Integration: переключение mode в конфиге отражается в событии.
- Metrics: инкременты счётчиков при генерации commentary и редакциях.

## Наблюдаемость / Безопасность

- Логи только с hash_prefix (никогда не raw snippet).
- Алерт при неожиданном включении `raw_ephemeral` в production (watchdog).
- Sanitization перед redaction (unicode normalization NFC).

## Миграция

1. Добавить секцию конфигурации.
2. Реализовать retention слой (простая функция/класс).
3. Расширить обработку завершения генерации (вставка summary в событие).
4. Метрики + тесты.
5. Обновить `API.md` / `Config-Registry.md`.

## Связанные документы

- ADR-0020 (Harmony Streaming Migration)
- ADR-0021 (Cap Semantics)
- ADR-0023 (Unexpected Order Handling)

## Открытые вопросы

- Нужен ли audit log включения raw_ephemeral (отложено: можно через отдельное событие config_change).
- Сжатие redacted_snippets (gzip threshold?) — отложено.
- Хэширование на уровне токенов vs строк — отложено.

## Примечания

Возможна интеграция hashed_slice в RAG index только при отдельном explicit consent механизме (вне MVP).
