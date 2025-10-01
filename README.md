# MIA4

Локальный модульный ИИ-ассистент (Mia).

## Быстрый старт

```powershell
# Клонирование
git clone https://github.com/Maximus1978/Mia4.git
cd Mia4

# Создание и активация окружения (Windows PowerShell)
python -m venv .venv
. .venv\Scripts\Activate.ps1

# Локали UTF-8 (на всякий случай)
$env:PYTHONUTF8=1; $env:PYTHONIOENCODING='UTF-8'

# Базовые зависимости
pip install --upgrade pip
pip install -r requirements.txt

# Запуск тестов
pytest -q
```

## Testing

Запуск тестов должен происходить в активированном виртуальном окружении. Для автоматизации добавлен батник `scripts/ensure_venv.bat`:

```powershell
scripts\ensure_venv.bat
pytest -q
```

Поведение батника:

1. Создаёт `.venv` если его нет.
2. Активирует окружение.
3. Устанавливает зависимости из `requirements.lock` (если есть) иначе `requirements.txt`.


Рекомендуется запускать локально и в CI перед любым `pytest`.

## Конфигурация

Слои:

1. `configs/base.yaml` – базовые значения.
2. `configs/overrides.local.yaml` – локальные (в .gitignore).
3. Переменные окружения с префиксом `MIA__` (двойной underscore → вложенность, пример `MIA__LLM__PRIMARY__ID`).

Доступ: `from core.config import get_config`.

Автоген: `scripts/generate_config_docs.py` создаёт снапшот `docs/ТЗ/Generated-Config.md` из Pydantic схем. Тест гарантирует синхронизацию. Ручной реестр: `docs/ТЗ/Config-Registry.md`.

## Модульная архитектура (S1–S7)

- Модульные схемы конфигурации (S1)
- ModuleManager + LLMModule (S2–S3)
- Capability routing по манифестам (S4)
- Стандартный `GenerationResult` (S5)
- Граф импортов + запреты зависимостей (S6)

Переходный слой `core.llm.factory` будет удалён после миграции вызовов на ModuleManager.

## GenerationResult

`generate_result()` возвращает: `text`, `usage.prompt_tokens`, `usage.completion_tokens`, `timings.total_ms`, `timings.decode_tps`. Используется для перф и наблюдаемости; строковый `generate()` оставлен для обратной совместимости.

## Разделение Reasoning / Final (Harmony)

Система перешла на единый формат Harmony: модель генерирует структурированные каналы (`analysis`, `final`). Потоковый адаптер (`HarmonyChannelAdapter`) инкрементально парсит спец‑токены `<|start|>assistant<|channel|>analysis|final<|message|>...<|end|>` и:

- Стримит токены `analysis` как SSE события `analysis` (не сохраняются в истории).
- Стримит финальные токены как события `token` (агрегируются клиентом в ответ).
- Вычисляет `reasoning_tokens`, `final_tokens`, `reasoning_ratio` без текстового маркера.
- При отсутствии Harmony спец‑токенов (несовместимый провайдер) весь вывод трактуется как `final` (reasoning=0) — без legacy fallback.

Legacy marker (`===FINAL===`) полностью удалён из кода, конфигов и тестов.

## Capability Routing

Манифесты моделей содержат `capabilities: ["chat", "judge", ...]`. Вызов через LLMModule: `get_provider_by_capabilities(["judge"])` выбирает подходящую модель, либо fallback на primary.

## Модели

Спецификация и манифесты описаны в `docs/ТЗ/Модели ИИ.md` и `docs/ТЗ/Config-Registry.md` (см. паспорта: [gpt-oss-20b-mxfp4](docs/ТЗ/passports/gpt-oss-20b-mxfp4.md), [phi-3.5-mini-instruct-q3_k_s](docs/ТЗ/passports/phi-3.5-mini-instruct-q3_k_s.md)).
Текущий спринт: реализация интерфейса провайдера, реестра манифестов и адаптера llama.cpp.

### Загрузка lightweight модели (phi)

Актуальный легковесный quant: `phi-3.5-mini-instruct-q3_k_s` (смена с `q4_0` 2025-08-26: прежний файл давал ошибку `invalid vector subscript`, подозрение на повреждённый GGUF).

Пример скачивания (скрипт ещё ссылается на старый id — будет обновлён в следующем спринте):

```powershell
python scripts/fetch_phi.py --model phi-3.5-mini-instruct-q3_k_s --repo microsoft/Phi-3.5-mini-instruct --filename Phi-3.5-mini-instruct_Uncensored-Q3_K_S.gguf
```

После выполнения файл появится в `models/` и манифест `llm/registry/phi-3.5-mini-instruct-q3_k_s.yaml` должен иметь совпадающий `checksum_sha256` (проверка выполняется при первой загрузке).

## Development

### Launcher (.bat) Dev Features

When using `scripts/launch/run_all.bat` or `scripts/launch/admin_run.bat`:

- Admin mode: `run_all.bat admin` sets `MIA_UI_MODE=admin` (verbose logging) and builds static UI by default.
- To force dev UI server with live reload use `MIA_UI_STATIC=0` before running the script.
- Dev harness (pre-stream / per-token delay sliders) & extended perf metrics panel become visible when localStorage key `mia.dev` = `1`.
  - Quick enable: open the UI with `?dev=1` (e.g. `http://localhost:3000/?dev=1`) or toggle "Developer mode" in settings.
  - The chat window will persist the flag; clear via browser devtools or uncheck the toggle.
- Reasoning block: last AI message shows a collapsible reasoning pane when the backend emits reasoning frames.
- Metrics panel shows: latency_ms, decode_tps, prompt/output tokens, context usage %, reasoning tokens and ratio when available.

Troubleshooting:
 
- If no dev controls appear: verify `?dev=1` param or set manually: `localStorage.setItem('mia.dev','1')`.
- If static build is served but you expected dev server: set `set MIA_UI_STATIC=0` before running `run_all.bat`.
- Passport mismatch toast appears only when backend detects config vs passport divergence on `max_output_tokens`.

### Fast-Path Smoke Mode (`MIA_LAUNCH_SMOKE`)

Для быстрых CI / smoke проверок предусмотрен флаг окружения `MIA_LAUNCH_SMOKE=1` (только Windows батник `run_all.bat`). При его установке:

1. Запускается и проходит health‑проверка backend.
2. Пропускаются `npm install`, Vite dev server и static build.
3. Всё равно выводится строка `UI launch URL=...` указывающая на backend (`http://127.0.0.1:8000/`) — контракт для тестов.

Преимущества: существенное сокращение времени в CI и отсутствие требования Node.js для smoke пути. Используется тестом `tests/launcher/test_launcher_smoke.py`.

Пример PowerShell:

```powershell
$env:MIA_LAUNCH_SMOKE="1"; scripts\launch\run_all.bat dev
```

Чтобы получить полный UI (live reload) — не задавайте переменную или явно установите `MIA_UI_STATIC=0` (для dev) / `MIA_UI_STATIC=1` (форс статической сборки).


Рекомендовано зафиксировать точные версии:

```powershell
pip freeze > requirements.lock
```
 
Для воспроизводимости в CI используйте lock.

## Структура (вырезка)

```text
core/
  config/
  llm/
  registry/
  events/
configs/
docs/
models/
memory/
modules/
reports/
```

## События и телеметрия

Система эмитит структурированные события (см. `docs/ТЗ/Events.md`). Пример `ReasoningPresetApplied` (фиксация выбранного reasoning режима до генерации):

```json
{
  "event": "ReasoningPresetApplied",
  "request_id": "<uuid>",
  "mode": "medium",
  "temperature": 0.7,
  "top_p": 0.92,
  "ts": 1734543453.123
}
```

Используйте для анализа распределения режимов и корреляции скорости / качества.

Дополнено (2025-08-26):

- ENV override аудит → метрика `env_override_total{path}` + маскированный структурированный лог применённых ключей.
- Валидация конфигурации → нормализация `n_gpu_layers` (отрицательные → 0), проверки диапазонов (`top_p` 0<..<=1, `max_output_tokens>0`). Ошибки инкрементируют `config_validation_errors_total{path,code}` и используют error types `config-out-of-range`, `config-invalid` (ADR-0006).
- Порог EventBus overhead формализован: ≤ 2% wall-clock генерации (Perf.md), подтверждение регрессии требует 3 повторов.

## Current Limitations

- EventBus v1 синхронный: нет async / backpressure / replay (запланировано v2).
- GenerationResult v2 внедрён; нет ещё авто-генерации схемы Events Registry.
- Нет Observability модуля (metrics/logging skeleton TBD).
- PerfCollector не реализован (только методология Perf.md).
- RAG / Memory / Evaluation — документированы как TBD.
- Нет async диспетчеризации событий.

## Performance

### CPU Baseline

Первый реальный прогон (20B Q4_K_M на CPU, n_gpu_layers=0):

| Metric | Value |
|--------|-------|
| load_ms | 2227 |
| gen_latency_s (54 токенов) | 8.2256 |
| tokens_per_s | 6.56 |
| llama_cpp_version | 0.3.16 |
| max_output_tokens (cfg) | 1024 |

Сбор выполнен скриптом `scripts/perf_cpu_baseline.py`.

Запуск (пример):

```powershell
$env:MIA_PRIMARY_ID="gpt-oss-20b-q4km"
$env:MIA_LLAMA_FAKE="0"     # реальный режим
$env:MIA__LLM__PRIMARY__N_GPU_LAYERS="0"
python scripts/perf_cpu_baseline.py
```

Отчёт сохраняется в `reports/perf_cpu_baseline.json` (путь можно переопределить `MIA_PERF_OUT`).

### CPU Tuning (n_threads / n_batch)

Свип показал улучшение tokens/s примерно +2%:

| n_threads | n_batch | tps |
|-----------|---------|-----|
| 8 | 256 | 6.69 |
| 8 | 128 | 6.65 |
| 8 | 512 | 6.57 |
| 16 | 512 | 6.50 |
| 16 | 256 | 6.47 |
| 4 | 128 | 6.34 |
| 4 | 256 | 6.27 |
| 16 | 128 | 6.25 |
| auto | 512 | 6.24 |
| 4 | 512 | 6.18 |
| auto | 256 | 4.73 |
| auto | 128 | 3.60 |

Рекомендация (CPU): `n_threads=8`, `n_batch=256`.

Локальный override пример:

```yaml
llm:
  primary:
    n_threads: 8
    n_batch: 256
```

Дальше: GPU smoke, scaling и long-context тесты.

### EventBus Overhead (micro)

Синтетический бенч (2000 GenerationCompleted emit): ~17.6µs на событие (avg 35.2ms total).
Скрипт: `python scripts/perf_eventbus_overhead.py`.
Примечание: включает работу метрик и копирование payload; не отражает реальный end-to-end latency, но даёт порядок величины (<0.02ms/evt).


## Лицензия

TBD.
