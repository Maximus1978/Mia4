# ADR-0010: TTS & Media Pipeline Contract

Status: Accepted (2025-08-25)

## Контекст
Необходим единый контракт для синтеза речи и генерации медиа (изображения/видео) с контролем ресурсов.

## Решение

TTS (SpeechService):

- Поддерживается один голос baseline: `mia_default`.
- Конфиг: `speech.enabled` (false), `speech.default_voice` ("mia_default"), `speech.sample_rate_hz` (22050, fixed for v1), `speech.cache_ttl_sec` (86400), `speech.p95_latency_target_ms` (500), `speech.p95_latency_max_ms` (800).
- События: Speech.Requested, Speech.Synthesized (см. UX документ).

MediaGenerationService:

- Ключи: `media.generation.enabled` (false), `media.max_image_resolution` (1_048_576), `media.max_video_duration_s` (10), `media.cache.max_mb` (512).
- Провайдеры stub по умолчанию (`media.image.provider`, `media.video.provider`).

Политика: запросы > лимитов отклоняются с error.type = RESOURCE_LIMIT.


## Варианты

1. Сразу несколько голосов — усложняет управление без необходимости.
2. Более высокая частота 24k — повышает размер без критической UX выгоды.

## Обоснование
Фокус на стабильном базовом опыте и метриках латентности.

## Последствия
Необходим кэш (LRU) для аудио/медиа — eviction по TTL + size.

## Безопасность / Наблюдаемость
Отслеживание p95 латентности и отказов (RESOURCE_LIMIT) позволит масштабировать позже.

## Связанные документы

- UX поведение Мии
- SECURITY_NOTES.md

## Примечания
Расширение голосов через manifests (voices/*.yaml) — будущий ADR.
