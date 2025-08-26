# INDEX (Classification)

Классификация документов ТЗ по доменам. Статусы: Stable / Draft / TBD / Planned / Deprecated.

| Категория | Документ | Статус | Назначение |
|-----------|----------|--------|------------|
| Архитектура | Архитектура проекта.md | Draft | Логическая структура и потоки |
| Архитектура | Application-Map.md | Draft | Диаграммы компонентов и последовательностей |
| Архитектура | ARCHITECTURE_GUARDS.md | Stable | Инварианты импортов и слоёв |
| Контракты | Events.md | Draft | Список событий (будет расширен EventBus) |
| Контракты | Config-Registry.md | Stable | Реестр ключей конфигурации |
| Контракты | Generated-Config.md | Stable | Автоген снапшот схем |
| Контракты | RAG.md | Draft | Процесс retrieve + события |
| Контракты | Memory.md | TBD | Интерфейсы памяти (будущее) |
| Контракты | Observability.md | TBD | Метрики / логи / трассировка |
| Контракты | Evaluation.md | TBD | Метрики качества и сценарии |
| Контракты | PerfCollector.md | TBD | Слой агрегации perf поверх событий |
| Конфигурация | planning.md | Draft | Roadmap фаз (будет приоритизация расширена) |
| Конфигурация | Migration-Policy.md | Planned | Правила schema_version эволюции |
| Конфигурация | Error-Taxonomy.md | Planned | Категоризация ошибок/ретраи |
| Безопасность | SECURITY_NOTES.md | Draft | Активы / угрозы / контроля |
| Перф | Perf.md | Draft | Методология и расширения |
| Перф | Характеристики ПК.md | Draft | Environment baseline (HW) |
| Glossary | Glossary.md | Draft | Термины |
| UX | UX поведение Мии.md | Draft | Поведенческие правила |
| Growth | Слой роста (рефлексивный слой).md | Draft | Рефлексия/инсайты |
| Emotion | Эмоциональный слой.md | Draft | FSM эмоций |
| Stack | Технологический стек.md | Draft | Технологии |
| Manifests | Модели ИИ.md | Draft | Манифесты моделей и capabilities |
| Backlog | Мульимодальные инструменты.md | Draft | Инструменты ввода/вывода |
| Backlog | UI.md | Draft | Пользовательский интерфейс |
| ADR | ../ADR/ADR-0000-Template.md | Draft | Шаблон решений |
| ADR | ../ADR/ADR-0006-Error-Taxonomy.md | Stable | Набор кодов ошибок |
| ADR | ../ADR/ADR-0011-EventBus-Architecture.md | Stable | Архитектура EventBus v1/v2 |
| ADR | ../ADR/ADR-0012-GenerationResult-Contract.md | Stable | Контракт GenerationResult v2 |

Примечание: устаревшие placeholders (ADR-0001, ADR-0002) заменены на принятые ADR-0012 и ADR-0011.

Поддержка: при добавлении нового публичного контракта обновлять таблицу.
