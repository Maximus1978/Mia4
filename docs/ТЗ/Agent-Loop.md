
Оркестратор одного шага диалога. Не хранит бизнес‑логику модулей, только последовательность вызовов + агрегацию результатов.

## Цикл обработки сообщения
| Шаг | Компонент | Вход | Выход |
|-----|-----------|------|-------|
| 1 | InputAdapter | raw user text/audio | message object |
| 2 | EmotionService (update) | message | emotion snapshot |
| 3 | ContextBuilder | history window + emotion + user profile | prompt_context |
| 4 | RAGRetriever | message.query | docs[] (scored) |
| 5 | PromptBuilder | context + docs | final_prompt |
| 6 | LLMClient | final_prompt | stream tokens |
| 7 | PostProcessor | tokens + docs | answer (text) |
| 8 | OutputMux | answer + emotion | UI events / voice task |
| 9 | Persistence | message + answer | diary entry id |
| 10 | Async Hooks | diary id | indexing, reflection trigger |

## События и подписки
| Event | Публикует | Подписчики |
|-------|-----------|------------|
| MessageReceived | UI | AgentLoop |
| MessageProcessed | AgentLoop | UI, Voice, Reflection |
| EmotionShifted | Emotion | UI, PromptBuilder |
| MemoryAppended | Persistence | Indexer, Reflection |
| RAGDocsRetrieved | RAG | Evaluator (опц), Logging |

## Временные требования (целевые)
| Секция | SLA (p95) |
|--------|----------|
| Emotion update | 30ms |
| RAG retrieval (k≤8) | 120ms |
| LLM first token | <1.2s (7B Q4) |
| Full answer (50 токенов) | <4s |

## Ошибки / деградация
| Сбой | Деградация |
|------|------------|
| RAG timeout | fallback: no docs, добавить notice в метаданные |
| Emotion classifier fail | reuse last snapshot |
| LLM overload | queue (max_wait 3s) → fast fallback model |
| Persistence fail | write to retry queue (disk) |

## Интерфейс
AgentLoop.process(message: MessageIn) -> Stream[AnswerChunk]
Stateless между сообщениями (кроме ссылки на сервисы).

## Не цели
Не проводить долгие фоновые задачи (рефлексия, переиндексация) – только инициировать.
Не решать подробную маршрутизацию мультимодальных pipeline – отдать специализированным сервисам.