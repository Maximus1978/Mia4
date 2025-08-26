# LLM Registry

Помести сюда YAML манифесты моделей `<id>.yaml`.

Пример:

```yaml
id: qwen2.5-7b-instruct
family: qwen
role: primary
path: models/qwen2.5-7b-instruct-q4_k_m.gguf
quant: q4_k_m
context_length: 32768
capabilities: [chat]
checksum_sha256: <sha256>
revision: r1
```
