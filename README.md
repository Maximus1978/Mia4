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

## Capability Routing

Манифесты моделей содержат `capabilities: ["chat", "judge", ...]`. Вызов через LLMModule: `get_provider_by_capabilities(["judge"])` выбирает подходящую модель, либо fallback на primary.

## Модели

Спецификация и манифесты описаны в `docs/ТЗ/Модели ИИ.md` и `docs/ТЗ/Config-Registry.md`.
Текущий спринт: реализация интерфейса провайдера, реестра манифестов и адаптера llama.cpp.

## Development

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
