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