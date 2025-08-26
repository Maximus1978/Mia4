# План развития (Post S7)

Источник: код-ревью 2025-08-25 + backlog в `.instructions.md` + текущие ТЗ.

Легенда статусов чекбоксов: [ ] не начато, [~] в процессе, [x] выполнено.
В Phase 0 различаем состояние спецификации (Spec) и реализации (Impl) для прозрачности.

## Фаза 0 — Опорные контракты

| # | Item | Description | Priority | Criticality | Effort | Spec | Impl | ADR |
|---|------|-------------|----------|-------------|--------|------|------|-----|
| 1 | GenerationResult v2 | version/status/error fields (contract) | P1 | Blocker | S | [x] Accepted | [x] Completed | ADR-0012 |
| 2 | EventBus 1.0 | sync bus + versioning rules | P1 | Blocker | M | [x] Accepted | [x] Completed | ADR-0011 |
| 3 | Error Taxonomy | unified error_type codes | P1 | High | S | [x] Accepted | [x] Enforced | ADR-0006 |
| 4 | Arch invariants AST | replace regex import graph | P2 | High | M | [x] Accepted | [x] Completed | ADR-0013 |

## Фаза 1 — Надёжность ядра

| # | Item | Description | Priority | Criticality | Effort | Status | ADR |
|---|------|-------------|----------|-------------|--------|--------|-----|
| 1 | Thread safety LLMModule | lock load/unload | P1 | High | S | Pending | - |
| 2 | ENV override audit | log applied env keys | P2 | Medium | S | Pending | - |
| 3 | Config validations | normalize n_gpu_layers etc | P2 | Medium | S | Pending | - |
| 4 | Bi-dir schema test | registry ↔ runtime match | P1 | High | M | Pending | - |
| 5 | AST import graph | (moved from Phase0 #3) | P2 | High | M | Pending | - |

## Фаза 2 — UI Shell (MVP)

Цель: минимальный пользовательский интерфейс для ранней интерактивной проверки ядра и последующего подключения модулей (RAG, Memory, PerfCollector). Запускается после завершения Phase 0 (контракты) и ключевых задач Phase 1 (потокобезопасность + bi-dir schema test).

Gate (должно быть завершено перед стартом UI):

- GenerationResult v2 Spec Accepted (ADR-0012) + Impl completed.
- EventBus v1 Spec Accepted (ADR-0011) + Impl completed.
- Thread safety LLMModule (Phase 1 #1).
- Bi-dir schema test (Phase 1 #4).

| # | Item | Description | Priority | Criticality | Effort | Status | ADR |
|---|------|-------------|----------|-------------|--------|--------|-----|
| 1 | UI Shell scaffold | Static build + routing (index + chat) | P1 | High | S | Planned | - |
| 2 | API endpoints | /generate (stream SSE), /health, /models | P1 | High | M | Planned | - |
| 3 | Streaming bridge | SSE or WebSocket token stream adapter | P1 | High | M | Planned | - |
| 4 | Session store (ephemeral) | In-memory chat history per tab | P2 | Medium | S | Planned | - |
| 5 | Model switcher | Dropdown (capability metadata) | P2 | Medium | S | Planned | - |
| 6 | Reasoning preset selector | UI → emits ReasoningPresetApplied | P2 | Medium | S | Planned | - |
| 7 | Perf mini panel | Last generation latency/tps (subscribe events) | P3 | Low | S | Planned | - |
| 8 | Placeholders panels | RAG context, Memory insights (TBD labels) | P3 | Low | S | Planned | - |
| 9 | Error surfacing | Display GenerationResult.status=error | P1 | High | S | Planned | - |
| 10 | Theming (dark/light) | CSS variables setup | P3 | Low | S | Planned | - |

Definition of Done (UI Phase):

- Real-time streaming ответа в chat панель.
- Переключение модели отражается в последующих генерациях.
- Отображение latency (total_ms) после завершения генерации.
- Ошибки отображаются единообразно (toast / inline) без раскрытия чувствительных данных.
- Все endpoints документированы в `API.md` и покрыты smoke тестами.

Риски: без Observability модуля ограничены в метриках → MVP собирает только локальные counters.

## Фаза 3 — Observability / Perf база

| # | Item | Description | Priority | Criticality | Effort | Status | ADR |
|---|------|-------------|----------|-------------|--------|--------|-----|
| 1 | Observability skeleton | metrics/logging scaffold | P1 | High | M | Pending | - |
| 2 | Metrics relocation | move metrics to module | P1 | High | S | Pending | - |
| 3 | PerfCollector core | rolling latency/tps window | P2 | Medium | M | Pending | - |
| 4 | Health snapshot API | /health module states | P2 | Medium | S | Pending | - |

## Фаза 4 — RAG фундамент

| # | Item | Description | Priority | Criticality | Effort | Status | ADR |
|---|------|-------------|----------|-------------|--------|--------|-----|
| 1 | RAG interfaces | retriever/ranker/embedder | P1 | High | M | Pending | - |
| 2 | VectorStore stubs | in-memory adapters | P2 | Medium | S | Pending | - |
| 3 | RAG config keys | top_k, weights, enabled | P1 | High | S | Pending | - |
| 4 | Dummy backend | no-impact when disabled | P1 | High | S | Pending | - |
| 5 | Retrieval metrics | retrieval_latency_ms etc | P2 | Medium | S | Pending | - |

## Фаза 5 — Memory слой

| # | Item | Description | Priority | Criticality | Effort | Status | ADR |
|---|------|-------------|----------|-------------|--------|--------|-----|
| 1 | Memory abstractions | writer/query protocols | P1 | High | M | Pending | - |
| 2 | RAG integration | memory hook retrieval | P2 | Medium | S | Pending | - |
| 3 | Memory events | ItemStored / Insight | P2 | Medium | S | Pending | - |

## Фаза 6 — Perf расширение

| # | Item | Description | Priority | Criticality | Effort | Status | ADR |
|---|------|-------------|----------|-------------|--------|--------|-----|
| 1 | Throughput split | prompt vs decode tps | P2 | Medium | S | Pending | - |
| 2 | Idle resource policy | LRU max_loaded models | P2 | Medium | M | Pending | - |
| 3 | Regression guard v2 | compare baseline JSON | P2 | Medium | M | Pending | - |

## Фаза 7 — EventBus расширение

| # | Item | Description | Priority | Criticality | Effort | Status | ADR |
|---|------|-------------|----------|-------------|--------|--------|-----|
| 1 | Async dispatch | queue + backpressure | P2 | Medium | M | Pending | - |
| 2 | Replay buffer | N last events retrieval | P3 | Low | S | Pending | - |

## Фаза 8 — Документация / синхронизация

| # | Item | Description | Priority | Criticality | Effort | Status | ADR |
|---|------|-------------|----------|-------------|--------|--------|-----|
| 1 | Events registry gen | auto events table + test | P2 | Medium | S | Pending | - |
| 2 | Guards link README | add limitations section | P1 | High | S | Pending | - |
| 3 | Current limitations | explicit README section | P1 | High | S | Pending | - |
| 4 | Changelog hook | validate changelog format | P2 | Medium | S | Pending | - |

## Фаза 9 — Advanced

| # | Item | Description | Priority | Criticality | Effort | Status | ADR |
|---|------|-------------|----------|-------------|--------|--------|-----|
| 1 | Capability negotiation | weights + rationale | P3 | Low | M | Pending | - |
| 2 | Path sandbox | models/ memory/ canonical | P2 | Medium | S | Pending | - |
| 3 | Performance.Degraded | event emission logic | P2 | Medium | S | Pending | - |

## Параллельные быстрые улучшения

- [x] Добавить field `version` (int) в GenerationResult (ADR-0012) для forward совместимости.
- [ ] TODO метки с ссылками на issues (по коду) — раздел в `ARCHITECTURE_GUARDS.md`.
- [ ] dotenv loader (опц.) — раздел в `Config-Registry.md`.

## Definition of Done

- [ ] Все новые ключи в `Config-Registry.md` + автоген обновлён.
- [ ] Events-Registry синхронизирован (генератор + тест).
- [ ] Import graph без циклов, расширенные правила соблюдены.
- [ ] Тесты: потокобезопасность LLM, RAG dummy, memory events, perf collector.

