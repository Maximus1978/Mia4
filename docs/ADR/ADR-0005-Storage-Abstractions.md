# ADR-0005: Storage Abstractions (Sessions, Attachments, Permissions)

Status: Accepted (2025-08-25)

## Контекст
Нужно отделить логику ядра от конкретной реализации хранения (файловая система сейчас) для упрощения миграции (S3, DB) и обеспечить sandbox.

## Решение

Интерфейсы (псевдо):
```python
class SessionStore:  # append-only messages log
    def append(self, message: dict): ...
    def tail(self, session_id: str, limit: int) -> list[dict]: ...

class AttachmentStore:
    def save(self, attachment_meta: dict, file_bytes: bytes): ...
    def open(self, attachment_id: str) -> bytes: ...

class PermissionStore:
    def grant(self, scope: str, decision: dict): ...
    def get(self, scope: str) -> dict|None: ...
    def audit_log(self) -> list[dict]: ...
```

Файловая реализация (MVP):

- messages: `data/sessions/<workspace>/<session>.jsonl`
- attachments: `data/attachments/<id>/<original_name>`
- permissions.json (append-only журнал + current map).

Индексирование вложений (гибридная политика):

1. При загрузке файл сохраняется c `status=stored`.
2. Если размер `<= attachments.embed.auto_threshold_mb` и `attachments.embed.on_upload=true` → автоматически ставится задача индексации (смена на `status=indexed` после успеха).
3. Если файл больше порога → остаётся `status=pending` до ручного запуска (кнопка «Индексировать» в UI) → затем очередь индексации.

Конфиг ключи:

- `attachments.embed.auto_threshold_mb` (int, default 10)
- `attachments.embed.on_upload` (bool, default true)

Sandbox: разрешённые корни перечислены в конфиге `storage.paths.*` + список `permissions.allowed_roots[]` (policy details: ADR-0008).

## Варианты

1. Немедленный переход к DB — преждевременно.
2. Использование единой key-value для всего — усложняет оффлайн отладку.

## Обоснование

Файловая модель прозрачна и легко тестируется; абстракция держит контракт минимальным.

## Последствия

Лёгкая замена бэкенда позже.

## Положительные

- Тестируемость, простая миграция.

## Отрицательные

- Нет транзакций; приемлемо для MVP.

## Безопасность / Наблюдаемость

Audit для permissions отделён → упрощён анализ инцидентов.

## Связанные документы

- Config-Registry.md
- SECURITY_NOTES.md
- ADR-0008 (Permissions & Sandbox)
 
## Примечания

VectorStore интерфейсы оформляются отдельно (RAG модуль ADR — future).
