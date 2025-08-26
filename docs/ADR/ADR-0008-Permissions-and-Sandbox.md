# ADR-0008: Permissions & Sandbox Model

Status: Accepted (2025-08-25)

## Контекст
Доступ к ресурсам (filesystem, microphone, camera, network, cloud) требует пользовательского гранта и аудита.

## Решение

Scopes пример: `filesystem.read`, `filesystem.write`, `microphone.capture`, `camera.capture`, `network.http`, `cloud.drive.read`.

Запрос:

```json
{"scope":"filesystem.read","reason":"Load project file","requested_ts":0}
```

Ответ (grant):

```json
{"scope":"filesystem.read","granted":true,"granted_ts":0,"ttl_sec":3600,"constraints":{"paths":["/project"]}}
```

Хранение: permissions.json (append-only log + current map). API PermissionStore (см. ADR-0005).

Sandbox валидация пути: нормализация → проверка входит ли в разрешённые roots (`permissions.allowed_roots[]`).

Конфиг ключи (Accepted):

- `permissions.auto_prompt` (bool, default true)
- `permissions.allowed_roots[]` (list[str], default ["."])


## Варианты

1. Хранить в общем конфиге — сложнее аудит.
2. База данных — premature.

## Обоснование
Отделение улучшает безопасность и отслеживание.

## Последствия
Нужен периодический GC истёкших TTL.

## Безопасность / Наблюдаемость
Централизованный аудит → детект аномалий.

## Связанные документы

- SECURITY_NOTES.md
- ADR-0005 Storage Abstractions

## Примечания
UI подтверждения должны включать описание scope + причину.
