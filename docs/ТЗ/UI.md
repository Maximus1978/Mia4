# UI (минимальный слой)

Фокус: быстрый текстовый диалог + визуальный намёк на эмоциональное состояние + точки расширения (плейсхолдеры).

## Компоненты (MVP)
| Компонент | Статус | Функция | События |
|-----------|--------|---------|---------|
| ChatPanel | active | Ввод/вывод сообщений | send(message) |
| EmotionBadge | passive | Цвет + tooltip состояния | subscribe EmotionShifted |
| DiaryTab (placeholder) | disabled | Будущий просмотр инсайтов | — |
| VoiceButton | placeholder | Триггер STT / TTS | toggle_voice |

## События UI → Core
| Event | Payload | Комментарий |
|-------|---------|-------------|
| UserMessage | {text, ts, temp?} | temp – опциональная температура LLM |
| VoiceStart | {} | Будущее расширение |
| VoiceStop | {} | — |

## Core → UI
| Event | Payload | Откуда |
|-------|---------|---------|
| MessageStream | {chunk, final?} | AgentLoop |
| EmotionShifted | {primary, valence, arousal} | Emotion |
| InsightCreated | {id, text, kind} | Reflection |

## Стейт менеджмент
Минимум глобального состояния: chat_log[], current_emotion, streaming_answer.
Zustand (или простой Context + reducer) достаточно.

## Не цели (MVP)
История инсайтов UI (только placeholder).
Продвинутые темы оформления.
Мультиязычная локализация (позже i18next).

## Будущее
Inline memory highlights.
Эмоциональные анимации аватара.
Дифф просмотр версий ответа (LLM сравнение).

## Ключевые параметры для UI (влияют на характер/стиль ответа):

### Базовые (показывать сразу):
- Model (primary / lightweight) – уровень качества vs скорость.
- Reasoning preset (low / medium / high) – пакетно меняет temperature/top_p.
- Temperature (0.0–1.2 разумно) – разнообразие / креатив.
- Top_p (0.8–0.95 типово) – концентрация распределения.
- Max output tokens – длина ответа / риск обрезки.
- Persona (user role prompt) – тон, “голос”.

### Дополнительные (Advanced раскрывающийся блок):
- System prompt (read-only просмотр) – база (для понимания что нельзя нарушить).
- Repetition penalty (добавить позже) – уменьшение повторов (1.05–1.25).
- Top_k (если включите в backend) – жёсткость отбора кандидатов (20–1000).
- Stop sequences (UI: мультистрочный) – ранняя остановка форматов.
- Presence / frequency penalties (при внедрении) – “новизна” vs повторяемость.
- Max persona length indicator (прогресс‑бар к лимиту 1200).

### Эксперт / Perf (скрыть по умолчанию, не про стиль, но влияют косвенно):
- Context length (truncate % slider / strategy) – влияет на доступную историю.
- n_threads / n_batch (CPU) – латентность → косвенно скорость и формирование стиля за счёт темпа показа.
- Abort generation (кнопка) – UX контроль.

### Метаданные/информеры (без редактирования):
- decode_tps (текущий поток) – обратная связь на настройки.
- first token latency – влияние контекста/модели.
- system_prompt_version + hash (tooltip) – воспроизводимость.

### Приоритет показа (слева направо в панели):
Model | Reasoning preset | Temperature | Top_p | Max tokens | Persona (expand)

### Связки:
- Изменение reasoning preset обновляет UI полей Temperature/Top_p (highlight временно).
- Ручное изменение temperature/top_p после preset помечает режим “custom”.

### Валидация / UX:
- Диапазоны (slider + numeric): temperature (0–2), top_p (0.1–1.0).
- Предварительный badge “Deterministic” при temperature ≤0.15 & top_p ≤0.85.
- Persona: live counter (chars / 1200), цвет → оранжевый >80%.

### Логгирование / события:
- GenerationStarted уже включает system_prompt_version/hash/persona_len → в UI можно рядом показывать (для дебага).
- Добавьте (позже) ReasoningPresetApplied отображение под строкой ввода (чтобы ясно что применяется).

### минимум для ощутимого контроля стиля:
1. Editable temperature + top_p (синхронизировано с preset).
2. Persona textarea.
3. Max tokens numeric.
4. Model switch (уже есть).
5. Read-only base prompt viewer.

### Опционально следующая волна:
- Stop sequences
- Repetition penalty
- Custom preset save (локально) 

### Точная структура состояния UI/JSON payload. 
