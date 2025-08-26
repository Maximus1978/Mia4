# Architecture Guards

Инварианты слоями (S8 plan foundation).

## Слои

1. Foundation: core.config, core.events, core.registry, core.dev.import_graph
2. Services: core.llm, core.metrics (переезд), future core.observability
3. Modules: modules/* (rag, perf, emotion, reflection, memory, observability)
4. Orchestration: core.modules.module_manager

## Правила

- Modules/* не импортируют core.modules.module_manager.
- perf/observability не импортируют внутренности llm (только публичный контракт GenerationResult + события).
- llm не импортирует perf/observability.
- Никаких импортов между sibling modules/*.
- import cycle forbid (тест import_graph_no_cycles).
- Публичные контракты (события, структуры результатов, новые конфиг ключи) требуют ADR перед реализацией (исключение: минорные поля наблюдаемости с пометкой Draft).

## Enforcement

- tests/core/test_import_graph_no_cycles.py (обновлять forbidden_edges при добавлении модулей).
- Предложено: ast-based парсер (замена regex) — задача в planning.

## Будущие

- Capability negotiation расширит правила (feature flags) — добавит слой capability policies.
- Replay buffer (EventBus v2) потребует ограничения памяти и чёткой политики очистки.
