"""Model registry stubs (moved from src/core).

Responsibilities:
- Load all manifest YAML files from llm/registry
- Validate schema (see docs/ТЗ/Модели ИИ.md, section 9.1)
- Provide lookup by model id / role
- Verify checksum (unless skip)

Future:
- Hot reload on manifest change (optional)
- Caching parsed manifests
"""
