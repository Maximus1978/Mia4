# ADR-0004: Data Schemas & Meta Prefixes

Status: Accepted (2025-08-25)

## Контекст
Нужны канонические минимальные схемы для сообщений, вложений и артефактов рефлексии, а также соглашение по префиксам метаданных для предотвращения коллизий.

## Решение

Схемы (JSON shape, поля могут расширяться, обязательные обозначены):

Message:
```json
{
  "id": "uuidv7", "workspace_id": "uuidv7", "session_id": "uuidv7", "ts": 0,
  "role": "user|assistant|system",
  "text": "...",
  "meta": {
    "model_id": "?",
    "tokens": {"prompt": 0, "completion": 0},
    "rag_context_ids": [], "emotion": "?", "tone": "?", "attachments": []
  }
}
```

Attachment:
```json
{
  "id": "uuidv7", "session_id": "uuidv7", "workspace_id": "uuidv7", "ts": 0,
  "filename": "...", "mime": "...", "size_bytes": 0,
  "status": "stored|indexed|error",
  "meta": {"hash": "...", "embedding_model": "?", "workspace_id": "?"}
}
```

Reflection Insight:
```json
{"id":"uuidv7","ts":0,"type":"theme|insight","text":"...","source_ids":[],"novelty_score":0.0,"meta":{}}
```

Preference:
```json
{"user_id":"default","updated_ts":0,"traits":{"formality":0,"depth":0,"playfulness":0},"counters":{"empathy_prompts":0,"intimacy_shift":0},"meta":{}}
```

MediaAsset:
```json
{"id":"uuidv7","type":"image|video|audio","format":"png|mp4|wav","status":"pending|ready|error","source":"generated|captured|uploaded","created_ts":0,"meta":{"duration_ms":0,"width":0,"height":0,"model_id":"?","prompt":"?"}}
```

Резерв префиксов внутри meta ключей (строковые ключи верхнего уровня meta):
`sys_`, `rag_`, `mem_`, `user_`, `media_`, `tts_`, `pref_`, `diag_` (финализировано).

Пользовательские ключи без префикса запрещены (валидатор отклоняет).

## Варианты
1. Свободные meta ключи — риск коллизий.
2. Иерархия объектов вместо префиксов — повышенная вложенность, сложнее фильтровать.

## Обоснование
Префиксы лёгкие, совместимы с плоскими лог-хранилищами и не мешают JSON flatten.

## Последствия
Требуется валидатор meta при записи.

## Безопасность / Наблюдаемость
Отделение системных (`sys_`) от пользовательских упрощает маскирование.

## Связанные документы

- UX поведение Мии (теперь содержит только persona — архитектурная часть перенесена в ADR/Events/Config-Registry)
- Events.md
 
## Примечания
В будущем возможно добавить регистрацию префиксов в конфиге.
