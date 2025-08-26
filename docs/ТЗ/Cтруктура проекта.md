# Структура проекта

Документ описывает ФИЗИЧЕСКУЮ структуру репозитория (что где лежит). Логическая архитектура: см. `Архитектура проекта.md`, диаграммы: `Application-Map.md`.

Минимальная, модульная, 1 факт → 1 место. Никаких «src/» ради src – каждый каталог осмыслен.

## Корень

| Файл / папка | Назначение |
|--------------|-----------|
| README.md | Быстрый старт + архитектурные акценты (S1–S7) |
| .instructions.md | Правила и чеклист спринтов (S1–S7 [x]) |
| configs/ | YAML (`base.yaml`, `overrides.local.yaml`), ENV MIA__* |
| docs/ | Документация (INDEX, ТЗ, changelog, автоген `Generated-Config.md`) |
| core/ | Ядро: config loader, llm, modules manager, events, registry, metrics |
| modules/ | Плагины (будущие rag, emotion, reflection, perf, observability) |
| infrastructure/ | Реализации адаптеров (db, vector, audio) |
| scripts/ | Утилиты запуска / обслуживания |
| tests/ | Тесты |
| memory/ | Runtime артефакты (snapshots, temp) |
| models/ | Модельные файлы (GGUF, classifiers) |
| reports/ | Автогенерируемые отчёты (perf JSON, метрики) |
| llm/ | Статические манифесты моделей (registry/*.yaml) |

## core/

| Пакет / файл | Назначение |
|--------------|-----------|
| config/ | Модульные схемы + агрегатор (migration legacy → schema_version) |
| llm/ | ModelProvider, адаптеры (llama.cpp), GenerationResult |
| llm/agent_ops.py | Высокоуровневые операции judge/plan (эмиссия событий) |
| events/ | Типы событий + шина (emit) — контракт для модулей |
| registry/ | Парсинг и индекс манифестов моделей |
| metrics.py | Заготовка метрик (будет вынесено в observability/perf) |
| modules/module_manager.py | ModuleManager + LLMModule (routing, capabilities) |
| dev/import_graph.py | Анализ импортов (арх. инвариант S6) |
| logging.py (позже) | Настройка structlog |
| memory.py (позже) | CRUD для памяти (diary/insight/theme) |

## modules/ (пример)

rag/, emotion/, reflection/, voice/, vision/, perf/, observability/ (план)

| Файл | Назначение |
|------|-----------|
| manifest.yaml | name, version, events(subscribe/publish), config_keys |
| service.py | Основная логика модуля |
| README.md | Локальные детали (только специфичные) |

## infrastructure/

db/ (инициализация sqlite, миграции), vector/ (qdrant client wrapper), audio/ (whisper, piper), cache/

## configs/

`base.yaml` → `overrides.local.yaml` → ENV (MIA__). Модульные Pydantic схемы (S1). Legacy миграция: автодобавление schema_version=1.

## tests/

| Каталог | Назначение |
|---------|-----------|
| contracts/ | Контрактные тесты API / events |
| modules/ | Тесты модулей (unit + интеграция узкая) |
| data/ | Фикстуры |

## scripts/

run_dev.py, prewarm_embeddings.py, eval_rag.py, export_snapshot.py,
perf_cpu_baseline.py, perf_tune_cpu.py, perf_gpu_smoke.py, perf_long_context.py, compare_models.py, generate_config_docs.py

## Ownership (ответственность)

| Область | Владелец (каталог) |
|---------|--------------------|
| Эмоции | modules/emotion |
| RAG | modules/rag |
| Рефлексия | modules/reflection |
| Конфиги | core/config/loader.py + schemas + configs/ |
| События | core/events.py |
| Инфраструктура БД | infrastructure/db |
| Логирование | core/logging.py |
| Метрики/Perf | core/metrics.py (старт) + scripts/perf_* + Perf.md |
| Module orchestration | core/modules/module_manager.py |
| Арх. инварианты | core/dev/import_graph.py + тест import_graph_no_cycles |

## Принципы

- Не дублировать схемы (SSOT в core.config.schemas + автоген snapshot).
- Generated-Config.md = автоген; Config-Registry.md = расширенные заметки.
- ModuleManager — единственная точка оркестрации (модули не импортируют его).
- Capability routing через манифесты (fallback → primary).
- GenerationResult — унифицированный результат (text, usage, timings).
- Import graph тест защищает слои (S6).
- Нет папки src/ — корень = смысловые зоны.
- Perf артефакты → reports/ + Perf.md.

## Будущее

module registry (INDEX из manifest.yaml), health-report модулей, perf collector (events → агрегаты), observability (Prometheus, structured logging), RAG pipeline, emotion FSM, nightly reflection.
