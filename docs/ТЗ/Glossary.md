# Glossary

1 факт → 1 термин → 1 определение.

| Термин | Определение | Где используется (основной) |
|--------|-------------|-----------------------------|
| Agent-Loop | Оркестратор одного шага диалога (pipeline ввода → ответ) | Agent-Loop.md |
| EmotionSnapshot | Объект {primary, valence, arousal} текущего состояния | Эмоциональный слой |
| Reflection (Growth Layer) | Пакет процессов генерации themes / insights | Слой роста (рефлексивный слой) |
| Insight | Сжатое наблюдение о пользователе с novelty_score | Слой роста |
| Diary Entry | Сырое сообщение (пользователь/Мия) с метаданными | Reflection, RAG |
| RAG | Retrieval augmented generation: гибридный поиск + LLM | RAG |
| Hybrid Retrieval | Комбинация BM25 + векторных скорингов с нормализацией | RAG |
| Persona | Набор инвариантных правил поведения Мии | UX поведение Мии |
| Manifest (module) | YAML файл описания модуля (events, config) | Архитектура проекта |
| Event Bus | Лёгкий Pub/Sub слой для внутренних событий | Архитектура проекта |
| Insight Novelty | 1 - cosine(existing_mean, candidate) | Слой роста |
| EmotionShifted | Событие смены primary эмоции | Эмоциональный слой |
| MemoryAppended | Событие добавления diary entry | RAG, Reflection |
| PromptBuilder | Компонент сборки финального промпта | Agent-Loop |
| KV Cache | Контекст LLM (attention memory) между токенами | Технологический стек |
| Tool | Изолированный модуль действия вне текста (audio, file, web) | Мульимодальные инструменты |

Расширение: добавлять в алфавитном порядке.
