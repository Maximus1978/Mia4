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
| 1 | Thread safety LLMModule | lock load/unload | P1 | High | S | [x] Done | - |
| 2 | ENV override audit | log applied env keys | P2 | Medium | S | [x] Done | - |
| 3 | Config validations | normalize n_gpu_layers etc | P2 | Medium | S | [x] Done | - |
| 4 | Bi-dir schema test | registry ↔ runtime match | P1 | High | M | [x] Done | - |
| 5 | AST import graph | (moved from Phase0 #3) | P2 | High | M | [x] Done | ADR-0013 |

## Фаза 2 — UI Shell (MVP) (ЗАВЕРШЕНО)

Все цели выполнены (см. CHANGELOG 2025-08-31). Gate пройден. Секция заархивирована в snapshot.

## Спринты Phase 3 (переструктурировано)

### Sprint 3A – Performance & Control Enablement

Цель: прозрачность модели и параметров + baseline производительности.

| # | Item | Description | Priority | Effort | Status | ADR |
|---|------|-------------|----------|--------|--------|-----|
| 1 | Model Passports | sampling_defaults + performance_hints + hash | P1 | M | Planned | ADR-0016 |
| 2 | Sampling controls UI | temperature/top_p/max_tokens editable + preset sync | P1 | M | Planned | - |
| 3 | Stub flag exposure | /models returns stub + UI badge + test | P1 | S | Planned | - |
| 4 | Stop sequences | llm.stop config + trimming + fallback marker | P1 | M | Planned | - |
| 5 | Reasoning ratio alert | metric + threshold test | P2 | S | Planned | - |
| 6 | Perf baseline snapshot | multi-run capture (fast + primary) | P1 | M | Planned | ADR-0017 |
| 7 | Sampling origin tagging | origin fields in GenerationStarted | P1 | S | Planned | - |
| 8 | Testing strategy doc | fast_only / primary_perf markers | P2 | S | Planned | - |

Exit Criteria 3A: baseline.json создан; UI отражает изменяемые sampling значения; stop_reason=stub и метрика alerts работают.

### Sprint 3B – Observability & Stability Hardening

| # | Item | Description | Priority | Effort | Status | ADR |
|---|------|-------------|----------|--------|--------|-----|
| 1 | PerfCollector | rolling p50/p95 latencies + decode_tps | P1 | M | Planned | ADR-0017 |
| 2 | Regression guard | compare baseline vs new run | P1 | M | Planned | - |
| 3 | Abort generation (server) | cancel token, stop_reason=cancelled | P1 | M | Planned | - |
| 4 | Events registry drift test | auto table + test | P2 | S | Planned | - |
| 5 | Idle unload policy | unload idle heavy models + metric | P2 | S | Planned | - |
| 6 | Hash exposure | system prompt & passport hash in /models | P2 | S | Planned | - |

Exit Criteria 3B: cancel действительно сокращает вывод; regression guard PASS.

### Sprint 3C – Harmony & Prompt Layering + Obsidian

| # | Item | Description | Priority | Effort | Status | ADR |
|---|------|-------------|----------|--------|--------|-----|
| 1 | Harmony Stage 2 | streaming analysis channel | P1 | M | Planned | ADR-0014 upd |
| 2 | Marker removal path | disable marker when stop sequences stable | P1 | S | Planned | - |
| 3 | N-gram tuning | suppression_count metric | P2 | S | Planned | - |
| 4 | Prompt layering | base + passport + persona + dynamic | P1 | M | Planned | ADR-0018 |
| 5 | Obsidian persona ingest | read-only sync persona.md -> hash | P1 | S | Planned | ADR-0018 |
| 6 | Prompt viewer UI | display layered prompt + hashes | P2 | S | Planned | - |

Exit Criteria 3C: analysis канал в UI без финальной буферизации; persona из Obsidian отражается в событиях.

### Perf Parity Gate

Требования до начала RAG реализации:

- p95 first_token_latency GPT-OSS ≤ baseline +10%.
- decode_tps median ≥ baseline -10%.
- reasoning_ratio alerts rate < порога.
- Cancel & stop sequences стабильны.
- PerfCollector + regression guard зелёные.

### RAG (ОТЛОЖЕНО – только дизайн до Gate)

| # | Item | Description | Priority | Effort | Status | ADR |
|---|------|-------------|----------|--------|--------|-----|
| 1 | Retrieval architecture ADR | VectorStore/Retriever contracts | P1 | M | Planned | ADR-0019 |
| 2 | VectorStore interface | no-op impl + tests | P2 | S | Planned | - |
| 3 | Retriever fusion strategy | weighted RRF spec | P2 | S | Planned | - |
| 4 | Config placeholders | rag.enabled / strategies | P2 | S | Planned | - |

Implementation начнётся только после Perf Parity Gate.

 
## (Deprecated Section) Former Phase 3 Table

Заменено новой структурой Sprint 3A/3B/3C.

## (Deprecated Section) Former Phase 4 — RAG фундамент

| # | Item | Description | Priority | Criticality | Effort | Status | ADR |
|---|------|-------------|----------|-------------|--------|--------|-----|
| 1 | RAG interfaces | retriever/ranker/embedder | P1 | High | M | Pending | - |
| 2 | VectorStore stubs | in-memory adapters | P2 | Medium | S | Pending | - |
| 3 | RAG config keys | top_k, weights, enabled | P1 | High | S | Pending | - |
| 4 | Dummy backend | no-impact when disabled | P1 | High | S | Pending | - |
| 5 | Retrieval metrics | retrieval_latency_ms etc | P2 | Medium | S | Pending | - |

## (Deprecated Section) Former Phase 5 — Memory слой

| # | Item | Description | Priority | Criticality | Effort | Status | ADR |
|---|------|-------------|----------|-------------|--------|--------|-----|
| 1 | Memory abstractions | writer/query protocols | P1 | High | M | Pending | - |
| 2 | RAG integration | memory hook retrieval | P2 | Medium | S | Pending | - |
| 3 | Memory events | ItemStored / Insight | P2 | Medium | S | Pending | - |

## (Deprecated Section) Former Phase 6 — Perf расширение

| # | Item | Description | Priority | Criticality | Effort | Status | ADR |
|---|------|-------------|----------|-------------|--------|--------|-----|
| 1 | Throughput split | prompt vs decode tps | P2 | Medium | S | Pending | - |
| 2 | Idle resource policy | LRU max_loaded models | P2 | Medium | M | Pending | - |
| 3 | Regression guard v2 | compare baseline JSON | P2 | Medium | M | Pending | - |

## (Deprecated Section) Former Phase 7 — EventBus расширение

| # | Item | Description | Priority | Criticality | Effort | Status | ADR |
|---|------|-------------|----------|-------------|--------|--------|-----|
| 1 | Async dispatch | queue + backpressure | P2 | Medium | M | Pending | - |
| 2 | Replay buffer | N last events retrieval | P3 | Low | S | Pending | - |

## (Deprecated Section) Former Phase 8 — Документация / синхронизация

| # | Item | Description | Priority | Criticality | Effort | Status | ADR |
|---|------|-------------|----------|-------------|--------|--------|-----|
| 1 | Events registry gen | auto events table + test | P2 | Medium | S | Pending | - |
| 2 | Guards link README | add limitations section | P1 | High | S | Pending | - |
| 3 | Current limitations | explicit README section | P1 | High | S | Pending | - |
| 4 | Changelog hook | validate changelog format | P2 | Medium | S | Pending | - |

## (Deprecated Section) Former Phase 9 — Advanced

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

