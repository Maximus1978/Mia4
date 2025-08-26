# ServiceRegistry (Spec Draft)

Цель: предоставлять модулям возможность находить сервисы по capability без жёстких импортов.

## API (черновик)

```python
class ServiceRegistry:
    def register(self, capability: str, provider: Any): ...
    def get(self, capability: str) -> Any: ...  # raises KeyError
    def optional(self, capability: str) -> Any|None: ...
```

## Правила

| Rule | Описание |
|------|----------|
| Capability namespace | kebab-case (e.g. llm.generate, rag.retrieve) |
| Registration | Производится модулем в своём init после загрузки конфигурации |
| No global singletons | Только через registry |
| Introspection | `list_capabilities()` (позже) для диагностики |

## Примеры

| Capability | Provider Interface |
|------------|--------------------|
| llm.generate | LLMModule.generate(prompt,...)->GenerationResult |
| rag.retrieve | RAGModule.retrieve(query,...)->list[Chunk] |
| memory.query | MemoryQuery.search_insights/recent_dialog |
| speech.synthesize | SpeechService.synthesize(text)->AudioAsset |

## Связанные

- Application-Map.md
- ADR-0011 (EventBus) — косвенно, через внедрение обработчиков
- ADR-0012 (GenerationResult)
