# Data Schema (skeleton)

Global notes: define all tables, primary keys, indices, retention.

## Tables

| Table | Field | Type | Nullable | Index | Description |
|-------|-------|------|----------|-------|-------------|
| messages (JSONL) | id | uuidv7 | no | pk | Message id |
|  | session_id | uuidv7 | no | idx_session | Сессия |
|  | workspace_id | uuidv7 | no | idx_workspace | Workspace scope |
|  | role | enum(user,assistant,system) | no |  | Роль |
|  | text | text | no | fulltext(opt) | Содержимое |
|  | meta | object | yes |  | Расширения (префиксы ADR-0004) |
| attachments_meta (jsonl) | id | uuidv7 | no | pk | Attachment id |
|  | session_id | uuidv7 | yes | idx_att_sess | Связь сессия |
|  | workspace_id | uuidv7 | no | idx_att_ws | Scope |
|  | mime | string | no |  | MIME |
|  | size | int | no |  | Bytes |
|  | status | enum(stored,pending,indexed) | no | idx_status | Индексация |
| permissions_log (jsonl) | ts | float | no | idx_ts | Время события |
|  | scope | string | no | idx_scope | Имя разрешения |
|  | decision | enum(granted,denied) | no |  | Решение |
|  | ttl_sec | int | yes |  | Время жизни |
| insights | id | uuidv7 | no | pk | Insight id |
|  | summary | text | no | fulltext | Краткое содержание |
|  | novelty_score | float | no | idx_novel | Новизна |
|  | source_ids | array(uuidv7) | no |  | Первичные элементы |
| reflection_run | id | uuidv7 | no | pk | Run id |
|  | started_ts | float | no | idx_started | Время старта |
|  | duration_ms | int | yes |  | Длительность |
|  | trigger | string | yes |  | Тип запуска |
| media_cache | id | uuidv7 | no | pk | Media id |
|  | media_type | enum(audio,image,video) | no | idx_type | Тип |
|  | path | string | no |  | Файл |
|  | size | int | no |  | Bytes |
|  | created_ts | float | no | idx_created | Кеширование |

## Qdrant Payload (skeleton)

| Key | Type | Description | Required |
|-----|------|-------------|----------|

## Retention Policies (skeleton)

| Artifact | Retention | Rotation Strategy | Notes |
|----------|-----------|-------------------|-------|

| Artifact | Retention | Rotation Strategy | Notes |
|----------|-----------|-------------------|-------|
| messages | 90d (draft) | архив в cold storage | PII scrub (future) |
| attachments_meta | 180d | prune orphaned | Основано на доступе |
| permissions_log | 30d | rolling window | Экспорт в SIEM |
| insights | keep | n/a | компактно |
| reflection_run | 30d | rolling | агрегируется в insights |
| media_cache | 7d | size+ttl | Лимит media.cache.max_mb |

TODO: finalize after privacy review.
