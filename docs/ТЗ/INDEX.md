# INDEX

Основной индекс доменных документов. См. также классификацию в `INDEX_CLASSIFICATION.md`.

| # | Документ | Файл | Назначение | См. также |
|---|----------|------|------------|-----------|
| 1 | Что такое проект Мия | Что такое проект Мия (из чего состоит).md | Обзор компонентов платформы | Glossary.md, Архитектура проекта.md |
| 2 | Архитектура проекта | Архитектура проекта.md | Потоки, модули, взаимодействия | Application-Map.md, ARCHITECTURE_GUARDS.md |
| 3 | Application Map | Application-Map.md | Диаграммы последовательностей и связи | ServiceRegistry.md |
| 4 | Структура проекта | Cтруктура проекта.md | Файловая структура и ownership | ARCHITECTURE_GUARDS.md |
| 5 | Архитектурные инварианты | ARCHITECTURE_GUARDS.md | Инварианты импортов/слоёв | Cтруктура проекта.md |
| 6 | Agent Loop | Agent-Loop.md | Оркестрация шага генерации | Prompts.md, Harmony-Prompt-Draft.md |
| 7 | Harmony Prompt Draft | Harmony-Prompt-Draft.md | Черновик многоуровневого промпта | Prompts.md |
| 8 | Prompts | Prompts.md | Формат и слои промптов | Harmony-Prompt-Draft.md |
| 9 | Service Registry | ServiceRegistry.md | Регистр сервисов / модулей | Application-Map.md |
| 10 | Data Schema | Data-Schema.md | Структуры данных (если применимо) | Generated-Config.md |
| 11 | Модели ИИ | Модели ИИ.md | Манифесты, паспорта, capabilities | passports/*, Perf.md |
| 12 | Passports (директория) | passports/ | Паспортные файлы моделей | Модели ИИ.md |
| 13 | Config Registry | Config-Registry.md | Реестр конфиг ключей | Generated-Config.md |
| 14 | Generated Config Snapshot | Generated-Config.md | Автоген снапшот схем | Config-Registry.md |
| 15 | Events (человеческий) | Events.md | Документ событий | Generated-Events.md |
| 16 | Generated Events Snapshot | Generated-Events.md | Автоген событий | Events.md |
| 17 | Observability | Observability.md | Метрики/логи/трейсинг | PerfCollector.md |
| 18 | Perf Методология | Perf.md | Методология perf, KPI | PerfCollector.md, reports/* |
| 19 | Perf Collector | PerfCollector.md | Агрегация perf событий | Perf.md |
| 20 | Evaluation | Evaluation.md | Метрики качества / сценарии | Perf.md |
| 21 | RAG | RAG.md | Извлечение и контекст | Memory.md |
| 22 | Memory | Memory.md | Интерфейсы памяти (план) | RAG.md |
| 23 | Growth Layer | Слой роста (рефлексивный слой).md | Рефлексия/инсайты | UX поведение Мии.md |
| 24 | Emotion Layer | Эмоциональный слой.md | FSM эмоций | UX поведение Мии.md |
| 25 | UX Поведение | UX поведение Мии.md | Persona и поведенческие правила | Prompts.md |
| 26 | UI | UI.md | Минимальный UI | Мульимодальные инструменты.md |
| 27 | Multimodal Tools | Мульимодальные инструменты.md | Стандартизация tools | UI.md |
| 28 | Hardware Baseline | Характеристики ПК.md | Окружение / HW baseline | Perf.md |
| 29 | Glossary | Glossary.md | Термины | Что такое проект Мия (из чего состоит).md |
| 30 | Planning / Roadmap | planning.md | Фазы и приоритеты | INDEX_CLASSIFICATION.md |
| 31 | Security Notes | SECURITY_NOTES.md | Акторы, угрозы, меры | Observability.md |
| 32 | Error Taxonomy (ADR) | ../ADR/ADR-0006-Error-Taxonomy.md | Коды ошибок | ARCHITECTURE_GUARDS.md |
| 33 | EventBus Architecture (ADR) | ../ADR/ADR-0011-EventBus-Architecture.md | Архитектура EventBus | Events.md |
| 34 | GenerationResult Contract (ADR) | ../ADR/ADR-0012-GenerationResult-Contract.md | Контракт результата | Events.md |
| 35 | Synthetic ModelLoaded ADR | ../ADR/ADR-0029-Synthetic-Primary-ModelLoaded-Event.md | Событие при кеш-получении primary | Events.md |
| 36 | Freeze Prep Changelog (2025-09-07) | ../changelog/2025-09-07-freeze-prep.md | Снапшот состояния перед новым спринтом | CHANGELOG-* |

Обновляется вручную (будущая автоматизация `doc_sync` сверит наличие всех `.md`).



