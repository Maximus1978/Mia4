# INDEX (Classification)

Классификация документов ТЗ по доменам. Статусы: Stable / Draft / TBD / Planned / Deprecated.

| Категория | Документ | Файл | Статус | Назначение | Связанные |
|-----------|----------|------|--------|------------|-----------|
| Архитектура | Архитектура проекта | Архитектура проекта.md | Draft | Логическая структура и потоки | Application-Map.md, ARCHITECTURE_GUARDS.md |
| Архитектура | Application Map | Application-Map.md | Draft | Диаграммы компонентов и последовательностей | ServiceRegistry.md |
| Архитектура | Архитектурные инварианты | ARCHITECTURE_GUARDS.md | Stable | Инварианты импортов и слоёв | Cтруктура проекта.md |
| Архитектура | Agent Loop | Agent-Loop.md | Draft | Оркестрация шага генерации | Prompts.md |
| Архитектура | Service Registry | ServiceRegistry.md | Draft | Регистрация сервисов | Application-Map.md |
| Промпты | Prompts | Prompts.md | Draft | Форматы и слои | Harmony-Prompt-Draft.md |
| Промпты | Harmony Prompt Draft | Harmony-Prompt-Draft.md | Draft | Черновик многоуровневого промпта | Prompts.md |
| Конфигурация | Config Registry | Config-Registry.md | Stable | Реестр ключей | Generated-Config.md |
| Конфигурация | Generated Config | Generated-Config.md | Stable | Автоген схем | Config-Registry.md |
| Конфигурация | Planning | planning.md | Draft | Roadmap фаз | INDEX.md |
| Конфигурация | Data Schema | Data-Schema.md | Draft | Структуры данных | Evaluation.md |
| Контракты | Events | Events.md | Draft | Список событий | Generated-Events.md |
| Контракты | Generated Events | Generated-Events.md | Draft | Автоген событий | Events.md |
| Контракты | Evaluation | Evaluation.md | TBD | Метрики качества | Perf.md |
| Контракты | Error Taxonomy (ADR) | ../ADR/ADR-0006-Error-Taxonomy.md | Stable | Коды ошибок | Events.md |
| Контракты | GenerationResult Contract (ADR) | ../ADR/ADR-0012-GenerationResult-Contract.md | Stable | Контракт результата | Events.md |
| Контракты | Synthetic ModelLoaded ADR | ../ADR/ADR-0029-Synthetic-Primary-ModelLoaded-Event.md | Draft | Событие кеш-загрузки primary | Events.md |
| Модели | Модели ИИ | Модели ИИ.md | Draft | Манифесты моделей | passports/ |
| Модели | Passports | passports/ | Draft | Паспортные данные | Модели ИИ.md |
| RAG | RAG | RAG.md | Draft | Извлечение контекста | Memory.md |
| RAG | Memory | Memory.md | TBD | Интерфейсы памяти | RAG.md |
| Наблюдаемость | Observability | Observability.md | TBD | Метрики / логи / трассировка | PerfCollector.md |
| Наблюдаемость | Perf Collector | PerfCollector.md | TBD | Агрегация perf | Perf.md |
| Перформанс | Perf | Perf.md | Draft | Методология perf | reports/* |
| Перформанс | HW Baseline | Характеристики ПК.md | Draft | Окружение / HW | Perf.md |
| UX | UX Поведение | UX поведение Мии.md | Draft | Persona / правила | Prompts.md |
| Growth | Growth Layer | Слой роста (рефлексивный слой).md | Draft | Инсайты | UX поведение Мии.md |
| Emotion | Emotion Layer | Эмоциональный слой.md | Draft | FSM эмоций | UX поведение Мии.md |
| UI | UI | UI.md | Draft | Интерфейс | Мульимодальные инструменты.md |
| Tools | Multimodal Tools | Мульимодальные инструменты.md | Draft | Инструменты ввода/вывода | UI.md |
| Stack | Tech Stack | Технологический стек.md | Draft | Технологии | Архитектура проекта.md |
| Glossary | Glossary | Glossary.md | Draft | Термины | Что такое проект Мия (из чего состоит).md |
| Overview | Overview | Что такое проект Мия (из чего состоит).md | Draft | High-level обзор | Glossary.md |
| Security | Security Notes | SECURITY_NOTES.md | Draft | Активы / угрозы | Observability.md |
| ADR | ADR Template | ../ADR/ADR-0000-Template.md | Draft | Шаблон решений |  |
| ADR | EventBus Architecture | ../ADR/ADR-0011-EventBus-Architecture.md | Stable | Архитектура EventBus | Events.md |
| ADR | Synthetic ModelLoaded Event | ../ADR/ADR-0029-Synthetic-Primary-ModelLoaded-Event.md | Accepted | Кеш-событие загрузки | Events.md |

Примечание: при добавлении нового публичного контракта обновлять обе таблицы (`INDEX.md` и этот файл).
