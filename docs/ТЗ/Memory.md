# Memory (TBD – non-blocking)

Заглушка. Цель: долговременное хранение и выборка значимых единиц (insight, diary entry, theme) для обогащения RAG и рефлексии.

## Предметная область

| Entity | Пример полей | Примечание |
|--------|--------------|------------|
| DiaryEntry | id, role, text, ts, meta{emotion?, tokens} | Сырое сообщение |
| Insight | id, summary, novelty_score, source_ids[], ts | Производная сущность |
| Theme | id, label, support_count, updated_ts | Агрегированная категория |

## Интерфейсы (черновик)

```python
class MemoryWriter(Protocol):
    def append_diary(self, entry: DiaryEntry) -> None: ...
    def upsert_insight(self, insight: Insight) -> None: ...
    def update_theme(self, theme: Theme) -> None: ...

class MemoryQuery(Protocol):
    def recent_dialog(self, limit:int) -> list[DiaryEntry]: ...
    def search_insights(self, text:str, top_k:int) -> list[Insight]: ...
    def themes(self) -> list[Theme]: ...
```

## События (план)

| Event | Поля | Триггер |
|-------|------|---------|
| Memory.ItemStored | item_type, item_id | Любая вставка |
| Memory.InsightMerged | insight_id, merged_ids[], delta_score | Объединение похожих |
| Memory.ThemeUpdated | theme_id, support_count | Рост/изменение |

## Связь с RAG

- RAG.QueryRequested → MemoryQuery для недавних сообщений.
- Insight используется для контекстного резюмирования (входит в candidate set retrieve).

## Integration Contract (initial)

| From | To | Call | Inputs | Output | Notes |
|------|----|------|--------|--------|-------|
| RAG | MemoryQuery | recent_dialog | limit:int | list[DiaryEntry] | Для заполнения окна истории |
| RAG | MemoryQuery | search_insights | text:str, top_k:int | list[Insight] | Семантические подсказки |
| MemoryWriter | RAG (future) | event Memory.InsightMerged | insight_id | - | Инкрементальная переиндексация |

Canonical events см. `Events.md`.

## Безопасность / Ограничения

- Очистка PII (позже).
- TTL для DiaryEntry (конфиг) – Planned.
