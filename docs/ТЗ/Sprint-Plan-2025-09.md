# Спринт план (2025-09) — Harmony SSOT выравнивание без RAG

Цель спринта: довести UI/UX и контрактные части до соответствия SSOT Harmony по отмене генерации и синхронизации sampling-лимитов, не затрагивая реализацию RAG.

Релизный инкремент: видимая работающая функция в UI — кнопка Cancel с KPI-метрикой и корректная синхронизация sampling лимитов и «custom» режима.

## Область работ (Scope)

1) UI Cancel path + KPI (< 300ms, P95)
- Кнопка Cancel в UI активной сессии/запроса.
- Отмена запроса: вызов backend abort-роута, корректное завершение SSE с `status=cancelled`.
- Измерение end-to-end latency (UI click → SSE end) и запись метрики в UI-лог + консоль (dev) и в backend уже существующими событиями.
- Ненавязчивый toast «Отменено», скрывается авто через 3–5 сек.

2) Sampling UI sync (limits & custom)
- Отображение лимитов из `/models`: «<текущее> / <limit>» рядом с max_tokens.
- Авто‑clamp полей до лимитов модели; подсветка при достижении cap.
- Тег «mode=custom» при пользовательском override sampling.
- Сохранение пользовательского значения при смене модели, если оно ≤ нового лимита (в т.ч. сценарий 1024 → 512 → 1024).

3) ModelPassportMismatch (UI сигнал)
- При событии `ModelPassportMismatch` — ненавязчивый warning toast с ссылкой на docs.

4) Governance & Docs (non‑RAG)
- Принять: ADR‑0033 (Commentary Retention), ADR‑0034 (Tool Message Pipeline) — статусы → Accepted.
- Консолидированный changelog по cap & cancellation.
- Документация: UI Cancel path + KPI, Sampling UI sync (скриншоты/флоу при наличии).

5) CI smoke & линт
- CI job: backend API smoke (имеющиеся тесты) + UI unit (Vitest) и крошечный e2e smoke (опционально, без зависимостей).
- Линт + typecheck для UI (tsc) и Markdown‑линт docs.

Out‑of‑scope: реализация RAG, ingestion события, сторы и индексация.

## Acceptance Criteria

- Cancel
  - В UI есть кнопка Cancel, активна при генерации, пассивна в idle.
  - Нажатие приводит к `SSE status=cancelled`; отображён toast.
  - KPI: p95 UI‑замер < 300ms на локальном smoke, ≥3 прогона, результаты в логах.
- Sampling
  - UI показывает «<current> / <limit>» для max_tokens.
  - Авто‑clamp работает; подсветка при cap; «mode=custom» включается при override.
  - Значение пользователя сохраняется при смене модели, если ≤ нового лимита.
- Passport mismatch
  - При событии — warning toast + ссылка на docs.
- Docs & Governance
  - ADR‑0033, ADR‑0034 → Accepted; changelog обновлён.
  - Документация UI Cancel и Sampling sync обновлена.
- CI
  - CI запускает: API smoke, UI unit (Vitest), линты; билд зелёный.

## Тестовая стратегия (минимум)
- Unit (UI, Vitest)
  - Clamp логика, «mode=custom» тэг, кросс‑модельное сохранение значений.
- Contract
  - Маппинг события `ModelPassportMismatch` → UI‑toast (мок/фикстура события).
- Integration
  - UI cancel e2e через моковый backend или локальный lightweight run; проверка закрытия SSE и тоаста.
- Perf smoke
  - 3× замер cancel KPI; p95 < 300ms.
- Regression
  - Проверка, что при отсутствии override «mode=custom» не показывается; при cap подсветка включается.

## Инструменты и артефакты
- Код: `chatgpt-design-app/src` — кнопка, состояние запроса, отображение лимитов.
- Тесты: `chatgpt-design-app` (Vitest) + минимальный e2e-smoke (опционально).
- Документация: `docs/ТЗ/UI-Cancel-and-Sampling.md` (новая/обновлённая), changelog‑запись.
- CI: workflow `ci-smoke.yml` (lint + tests), runner Ubuntu/Windows.

## Риски и смягчение
- Flaky SSE закрытие: добавить небольшой backoff/таймаут в e2e; опереться на уже реализованный серверный backstop.
- Различие лимитов при переключении моделей: покрыть тестом «1024 → 512 → 1024» и ручной smoke в UI.
- Предупреждение multipart PendingDeprecation: временно подавить warning в pytest.ini; отследить апстрим.

## Связка с Harmony SSOT
- EP#6 Cancellation Semantics → UI кнопка + KPI (дозакрываем UI часть).
- EP#7 Sampling & Max Token Cap → UI sync (auto‑clamp, limit display, custom‑mode tag, cross‑model preservation).
- EP#13 Governance & ADR → Принятие ADR‑0033/0034 и консолидированный changelog.

## План работ (вехи)
- W1: UI Cancel button + KPI замер + unit/contract tests.
- W2: Sampling UI sync + unit tests + ModelPassportMismatch toast; CI smoke + docs + changelog; ADR‑0033/0034 Accepted.

## Готовность к релизу
- Все acceptance критерии зелёные; CI зелёный; дымовые отмена/лимиты проверены вручную.
