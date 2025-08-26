# SECURITY NOTES (Draft)

Минимальный baseline угроз и контролей. Документ расширяется перед добавлением внешних источников данных.

## Assets

| Asset | Описание | Защита сейчас |
|-------|----------|---------------|
| Model Files (models/) | GGUF / checkpoints | Checksum verify (event ChecksumMismatch) |
| Config (configs/*.yaml) | Параметры запуска | Pydantic валидация + schema_version миграция |
| Reports (reports/) | Perf и метрики | Локальный доступ только |
| Memory Data (memory/) | Будущие записи диалога / инсайты | Пока отсутствует |
| Logs | Structured events | Локальный stdout/файл |

## Threats (Draft)

| ID | Угроза | Риск | Комментарий |
|----|--------|------|-------------|
| T1 | Подмена модели (supply) | Высокий | Решается checksum + фикс пути |
| T2 | Чтение чувствительных данных из памяти | Средний | Требует ACL / шифрования (позже) |
| T3 | Отравление конфигурации ENV | Средний | Логировать применённые ENV overrides |
| T4 | Код в стороннем скрипте perf | Низкий | Изоляция venv, review scripts |
| T5 | Path traversal в загрузчике моделей | Средний | Ограничить base dir models/ |

## Controls / Planned

| Control | Статус | План |
|---------|--------|------|
| Checksum verify | Active | Расширить лог деталью алгоритма |
| Path sandbox (models/) | Planned | Внедрить canonical path проверку |
| ENV override audit | Planned | Логирование списка применённых ключей |
| Memory encryption at rest | Planned | После внедрения Memory |
| Access tiers (read/write) | Planned | Опциональный ACL уровень |

## Secure Coding Guidelines (минимум)

1. Запрещены eval/exec на входных данных.
2. Абсолютный путь модели формируется из базового каталога + относительного имени (без ..).
3. Никаких сетевых загрузок моделей без явной ADR.
4. Логирование ошибок без утечки чувствительных данных (обрезать длинные промпты > N токенов в логах).

## Open Questions

- Нужна ли подпись (GPG) для manifests? (пока нет).
- Нужно ли версионирование SECURITY_NOTES (отдельно)? (возможно через changelog).
