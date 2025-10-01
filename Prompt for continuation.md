# Continuation Prompt (Session Handoff) – 2025-09-30

## 1. Что сделано в текущей сессии

- Восстановлена телеметрия `ReasoningSuppressedOrNone`: `HarmonyChannelAdapter` получает `request_id`/`model_id`, событие и `reasoning_none_total` подтверждены unit-тестом.
- Добавлен счётчик `fused_marker_sanitizations_total{kind}` + расширены тесты `test_harmony_fused_sanitation.py` (включая residue-case).
- Внедрён временный UI scrub (`sanitizeFinalText` + `AIMessage` data hook) и обновлён UI контракт `final_message_sanitization.spec.tsx`.
- Обновлены `.instructions.md`, ADR-0013i addendum и новый changelog с фиксацией закрытых R3/R6/R8.
- Повторно прогнаны таргетные pytest (`tests/core/test_reasoning_none_telemetry.py`, `tests/core/test_harmony_fused_sanitation.py`) и Vitest (`tests/ui/final_message_sanitization.spec.tsx`) — всё зелёное.

## 2. Приоритетный план работ

### P0 (закрыто 2025-09-30)

1. ✅ **Reasoning-none телеметрия (R8 / INV-CH-ISO):** `set_context()` проброшен из `PrimaryPipeline`, unit `test_reasoning_none_telemetry.py` зелёный.
2. ✅ **Fused sanitation metric (R3 / INV-LEAK-METRICS):** helper `inc_fused_marker_sanitization` + расширенные backend тесты.
3. ✅ **UI fused scrub (R6 / INV-CH-ISO):** `sanitizeFinalText` + обновлённая UI спецификация; guard помечен как временный.

> Открытые хвосты ремедиации: duplicate-final тест (R4), SSE контракт на fused prefix (R10), обновление регистра инварианта INV-CH-ISO (R11), полный прогон + metrics snapshot (R12).

### P1 (возобновить после закрытия P0)

1. **Tool trace stub (INV-TOOL-TRACE, 8d):** dev-блок "No tool calls" + placeholder spec, затем реальный тест (8e).
2. **Контрактные тесты UI/API:** reasoning badge (5c), CAP badge (7f), cancelled badge (6b), first_token_latency (11e).
3. **ADR + API тест warning frame (13j):** формализовать `event: warning` и добавить проверку mismatch.
4. **Миграция reasoning ratio threshold (13k):**
   - Документировать ключ `llm.postproc.reasoning.ratio_alert_threshold` в `Config-Registry.md`.
   - UI полностью переключить на `/config` без localStorage fallback.
   - Ввести bi-directional тест.
5. **Удалить legacy `reasoningSanitization.ts` + тест** после подтверждённой чистоты (пост P0 scrub).

### P2 (при наличии ресурса)

1. Запуск RAG skeleton (12a–c) и HTML snapshot финального сообщения (из backlog).

## 3. Новые/уточнённые задачи и наблюдения

- Мониторим `fused_marker_sanitizations_total{kind}` и `reasoning_none_total{reason}` — собрать baseline до снятия guard.
- Задокументирована временная UI санитизация; необходимо завести follow-up на её удаление после стабилизации (см. R6).
- P1 фокус смещается на tool trace stub и контрактные UI/API тесты.
- Harmony SSOT аудит: канализация и метрики соответствуют, но контрактные тесты для финального SSE/Reasoning-none UI отсутствуют, INV-CH-ISO в ADR требует обновления, RAG skeleton (12a–12c) не стартовал.

## 4. Ключевые файлы и артефакты

- Backend: `core/llm/adapters.py`, `core/llm/pipeline/primary.py`, `core/metrics.py`.
- Frontend: `chatgpt-design-app/src/components/Chat/AIMessage.tsx`, `chatgpt-design-app/src/utils/sanitizeFinalText.ts`.
- Docs: `.instructions.md` (обновлено 2025-09-30), `docs/changelog/2025-09-30-harmony-remediation-r3-r8.md`, ADR-0013i addendum.
- Tests: `tests/core/test_reasoning_none_telemetry.py`, `tests/core/test_harmony_fused_sanitation.py`, `chatgpt-design-app/tests/ui/final_message_sanitization.spec.tsx`.

## 5. Статус инвариантов (2025-09-30)

| Invariant | Статус | Осталось |
|-----------|--------|---------|
| INV-CH-ISO | ✅ Восстановлен (guard временный) | Мониторинг fused санитайзера, снять after soak |
| INV-LEAK-METRICS | ✅ Обновлён | Отслеживать fused_marker_sanitizations_total baseline |
| INV-RATIO-VIS | UI работает | Контрактный тест (5c) |
| INV-CAP-UX | UI работает | Контрактный тест (7f) |
| INV-CANCEL-CLAR | UI работает | Контрактный тест |
| INV-FIRST-TOKEN | Backend+UI готовы | Контрактный тест (11e) |
| INV-TOOL-TRACE | ❌ Не реализован | Stub + контракт |
| INV-GOV-ADR | Частично | ADR warning frame |
| INV-CONFIG-BIDIR | ❌ Нет | Threshold migration + bi-dir тест |
| INV-RAG-MIN | Pending | RAG skeleton |

## 6. Риски и наблюдения

- Временный UI guard может скрыть редкие легитимные строки → держим логирование через `data-original`, снимаем после мониторинга.
- Интеграционные контрактные тесты (badges, warning frame) по-прежнему отсутствуют → следить за регрессиями.
- Tool trace UX всё ещё без stub — dev flow не сигнализирует отсутствие инструментов.

### Harmony SSOT: ключевые выводы

- ✅ Channel separation & observability: `HarmonyChannelAdapter` держит раздельные буферы, метрики (`reasoning_none_total`, `fused_marker_sanitizations_total`, `channel_merge_anomaly_total`) и события синхронизированы с ADR/SSOT.
- ⚠️ Contract coverage: нет автоматических SSE тестов на fused префикс и reasoning-none UI (R10, R5/R7) — необходимо для полного соответствия SSOT.
- ⚠️ Governance: INV-CH-ISO обновлён в инструкции, но формальный ADR/registry апдейт ещё не выпущен.
- 🚧 RAG readiness: этап 12a–12c Execution Plan пустой, SSOT требует минимальный RAG skeleton.
- 🔍 Validation cadence: выполнены только таргетные pytest/vitest; SSOT baseline подразумевает регулярный полный прогон + metrics snapshot (R12).

## 7. Рабочий стиль и соглашения

- Любое изменение публичного контракта → сначала ADR/SSOT + changelog.
- Observability first: метрики/события добавлять вместе с логикой.
- Нет magic numbers: thresholds только из конфигов/паспортов/fixtures.
- Один модуль — одна ответственность, единый источник правды (конфиг/паспорт).
- Контрактные тесты обязательны для новых/изменённых UI/streaming признаков.
- Финальный текст UI = исключительно sanitized `final_text` бэкенда; reasoning отдельно.

## 8. Следующее действие при старте новой сессии

Перейти к **P1.1 Tool trace stub (INV-TOOL-TRACE)**:

1. Зафиксировать dev-блок "No tool calls" + placeholder spec.
2. Подготовить контрактный тест (8e) и базовую документацию.
3. Параллельно завести тикет на снятие временного UI scrub после стабилизации метрик.

## 9. Чеклист перед merge ближайших изменений

- [x] Телеметрия Reasoning-none восстановлена, тесты зелёные.
- [x] Fused sanitation counter реализован + покрыт тестами.
- [x] UI scrub внедрён, UI контракт обновлён.
- [x] Обновлены `.instructions.md` и changelog.
- [x] Никаких lint/build ошибок (pytest + vitest таргетные прогнаны).

---

Используйте этот файл как стартовый промпт, чтобы продолжить закрытие P0 задач и вернуть кодовую базу в соответствие с SSOT.
