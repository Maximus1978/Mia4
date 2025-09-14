# ADR-0012: GenerationResult Contract (v2)

Status: Accepted (2025-08-25)

## Контекст

Нужен стабильный программный контракт возвращаемого результата генерации, независимый от внутренностей провайдера (llama.cpp). Версия v1 была имплицитна (text, tokens). V2 добавляет статус, usage и timings для perf/observability без утечки частных атрибутов.

## Структура (v2)

```json
{
  "version": 2,
  "status": "success|error",
  "text": "...",
  "usage": {"prompt_tokens": int, "completion_tokens": int},
  "timings": {"total_ms": int, "decode_tps": float},
  "sampling": {"temperature": float, "top_p": float, "top_k": int, "repeat_penalty": float, "min_p": float, "max_tokens": int, "filtered_out": ["param"...]?}?,
  "error": {"type": "error_type", "message": "..."}?  
}
```

## Правила

1. `status=error` → поле `error` обязательно; `text` может быть частично (обрезано) или пустым.
2. `decode_tps = completion_tokens / decode_phase_ms * 1000` (decode_phase_ms ⊆ total_ms).
3. Поля usage вычисляются до тримминга безопасности (безопасность может скорректировать `text`).
4. Поле `sampling` опционально: присутствует когда провайдер предоставляет параметры; `filtered_out` показывает отброшенные неподдерживаемые параметры.
5. Новые метрики / разделы добавляются только через MINOR bump version → payload.version=3.

## Mapping к событиям (v2)

- GenerationStarted: фиксирует начало (prompt_tokens, correlation_id).
- GenerationChunk: нулевой или более раз (seq монотонен, tokens_out кумулятивен).
- GenerationCompleted: одиночное терминальное; содержит status ok|error, агрегаты (output_tokens, latency_ms) и `result_summary` (вложенная структура с usage/timings/error/sampling).

Deprecated: GenerationFinished / GenerationFailed (v1) заменены на GenerationCompleted.

## Ошибки

Используют коды из ADR-0006.

## Тесты

`test_generation_result_contract.py` проверяет сериализацию и обязательность полей.

## Связанные

- Perf.md (decode_tps)
- ADR-0006 (Error Taxonomy)
- Events.md
