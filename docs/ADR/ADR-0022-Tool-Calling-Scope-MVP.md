# ADR-0022: Tool Calling Scope (MVP)

Status: Draft
Date: 2025-09-03

## Контекст

Необходимо ввести минимальный слой вызова инструментов (tool calling) в Harmony‑совместимом пайплайне без преждевременной сложности:

- У нас уже есть отдельные каналы (analysis, commentary, final).
- Требуется передавать в модель структурированные подсказки о доступных инструментах и парсить ответы.
- Нужен единый формат события для аудита и наблюдаемости.
- Нужно заложить эволюцию (multi-step chains, retention policy) без жёсткой фиксации детали реализации сейчас.

## Цели MVP

1. Минимальный синтаксис заголовка для объявления вызова инструмента.
2. Унифицированное событие `ToolCallProposed` (analysis → до исполнения).
3. Унифицированное событие `ToolCallExecuted` (результат выполнения + время, статус).
4. Базовый механизм ограничения (no nested tool recursion > 1, no concurrent tool calls в одном шаге).
5. Политика retention: анализ (analysis) — с `drop_from_history=true`; tool результаты входят в history только в компактном виде.
6. Возможность отключить tool calling глобально (config flag / passport capability).

## Нефункциональные требования

- Backward compatible: отсутствие tool синтаксиса → старая логика без изменений.
- Zero-cost idle: при отключённом флаге отсутствует доп. парсинг.
- Наблюдаемость: метрики количества предложенных и успешно выполненных tool calls.

## Решение

### Синтаксис (в ответе модели)

```xml
<tool name="<tool_name>" args>{
  "arg1": "value",
  "arg2": 123
}</tool>
```

Альтернативный укороченный формат (экспериментальный / может быть снят):

```text
<tool:<tool_name>>{"arg":"v"}
```
MVP парсер поддерживает оба, но второй помечает поле `deprecated_syntax=true` в событии для будущей телеметрии.

### Заголовок объявления (input prompt scaffolding)

Модель получает секцию:

```yaml
TOOLS:
- name: <tool_name>
  description: <one-line>
  schema: <JSON Schema excerpt or short args description>
END TOOLS
```
Включается только если tool calling активирован.

### Парсинг

- Регекс по тегам `<tool ...>` с извлечением name и JSON body.
- Валидация JSON → при ошибке эмитится событие `ToolCallParseError` и ответ игнорируется (может быть повтор шага без инструмента).

### События

- `ToolCallProposed { request_id, tool_name, raw_args, deprecated_syntax }`
- `ToolCallExecuted { request_id, tool_name, success, latency_ms, output_truncated, output_size_bytes }`
- `ToolCallParseError { request_id, raw_excerpt, error }`

### Конфиг

`tool_calling:` секция в `configs/base.yaml`:

```yaml
tool_calling:
  enabled: true
  max_depth: 1
  allow_deprecated_syntax: false
  retention:
    store_raw_tool_output: false
    max_output_bytes: 2048
```

### Ограничения (MVP)

- Нет параллельных вызовов в одном токен шаге.
- Нет авто‑повтора failed tool (делается вручную через повтор генерации).
- Нет агрегирующих составных результатов.

## Варианты

- JSON-only формат без тегов (риск коллизии с обычным текстом).
- YAML блоки (увеличивает размер prompt, сложнее валидировать потоково).
- Structured Output API (сложнее эмулировать в локальных моделях сейчас).

## Обоснование

- Теговый формат легко искать регексом и удалять из финального пользовательского вывода.
- Два синтаксиса → контролируемая телеметрия для выбора окончательного.
- Чёткие события → измеримость и эволюция.

## Последствия

### Положительные

- Быстрый путь к прототипированию инструментов.
- Минимум внедрения в существующий Harmony адаптер.
- Расширяемость (добавление атрибутов без ломающего изменения).

### Отрицательные

- Простой регекс может ошибочно цеплять ложные строки (edge cases) — требуется тестовая матрица.
- Два синтаксиса повышают сложность (уже запланированное снятие одного).

## Наблюдаемость

- Метрики:
  - `tool_calls_proposed_total{tool}`
  - `tool_calls_executed_total{tool,success}`
  - `tool_call_parse_errors_total`
- Логи warning при deprecated_syntax.

## Тестирование

- Unit: парсер (валидный тег, битый JSON, вложенный тег, пустой body).
- Unit: фильтр deprecated синтаксиса при `allow_deprecated_syntax=false`.
- Integration: полный цикл (model → proposed → executed → final).
- Contract: наличие новых событий и полей в EventBus.

## Миграция

- Добавить секцию конфигурации + в `Config-Registry.md`.
- Расширить адаптер парсером тегов (feature-flag).
- Добавить emission событий и метрики.
- Обновить `API.md` (раздел Tool Calling) + changelog.

## Связанные документы

- ADR-0016 (Passports) — источник sampling logic, не пересекается напрямую.
- ADR-0021 (Cap Semantics) — соседняя часть семантики выборок (orthogonal).
- Execution Plan Step 8 (Tool Calling Foundations).

## Открытые вопросы

- Ограничение по времени выполнения tool (timeout) — вынести в последующий ADR.
- Механизм цепочек (multi-step reasoning/tool) — последующий ADR.
- Аутентификация внешних инструментов — отдельный security ADR.

## Примечания

Будущий отказ от укороченного синтаксиса планируется после сбора статистики N≥500 вызовов.
