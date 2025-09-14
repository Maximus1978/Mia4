import re
from pathlib import Path

from core.config import as_dict, clear_config_cache

REGISTRY_PATH = Path('docs/ТЗ/Config-Registry.md')

# Explicit ignore lists (document reasons in comments). Empty initially.
IGNORE_REGISTRY_ONLY = {
    # Namespaces not yet implemented in runtime schemas/base.yaml
    'prompt.context.min_last_messages',
    'prompt.context.fraction',
    'session.title.auto_generate',
    'attachments.embed.auto_threshold_mb',
    'attachments.embed.on_upload',
    'permissions.auto_prompt',
    'permissions.allowed_roots',
    'persona.reminder_interval',
    'speech.enabled',
    'speech.default_voice',
    'speech.sample_rate_hz',
    'speech.cache_ttl_sec',
    'speech.p95_latency_target_ms',
    'speech.p95_latency_max_ms',
    'media.generation.enabled',
    'media.image.provider',
    'media.video.provider',
    'media.max_image_resolution',
    'media.max_video_duration_s',
    'media.cache.max_mb',
    # Observability consolidated into logging/metrics currently
    'observability.metrics.enabled',
    'observability.metrics.port',
    'observability.logging.level',
    'observability.tracing.enabled',
    # reflection.triggers not yet implemented in runtime schemas
    'reflection.triggers.token_threshold',
    'reflection.triggers.idle_seconds',
}
IGNORE_RUNTIME_ONLY = {
    # Container nodes not explicitly listed in registry (only their leaves)
    'llm', 'llm.primary', 'llm.lightweight',
    'embeddings', 'embeddings.main', 'embeddings.fallback',
    'rag', 'rag.hybrid', 'rag.normalize',
    'emotion', 'emotion.model', 'emotion.fsm',
    'reflection', 'reflection.schedule',
    'metrics', 'metrics.export',
    'logging', 'storage', 'storage.paths', 'system', 'perf', 'perf.thresholds',
    'modules'
}

KEY_COLUMN_PATTERN = re.compile(r'^\|\s*([^|]+?)\s*\|')


def extract_registry_keys(text: str) -> set[str]:
    keys: set[str] = set()
    in_table = False
    for line in text.splitlines():
        line = line.rstrip()
        if line.startswith('| Key path '):
            in_table = True
            continue
        if in_table:
            if not line.startswith('|'):
                # table ended
                break
            if line.startswith('|---'):
                continue
            m = KEY_COLUMN_PATTERN.match(line)
            if not m:
                continue
            raw = m.group(1).strip()
            if not raw or raw.lower() == 'key path':
                continue
            # arrays 'modules.enabled[]' -> treat as 'modules.enabled'
            key = raw.replace('[]', '')
            # wildcard maps like llm.optional_models.* -> keep prefix before .*
            if key.endswith('.*'):
                key = key[:-2]
            keys.add(key)
    return keys


def flatten_runtime(d: dict, prefix: str = '') -> set[str]:
    out: set[str] = set()
    for k, v in d.items():
        path = f'{prefix}{k}' if prefix == '' else f'{prefix}.{k}'
        if isinstance(v, dict):
            out |= flatten_runtime(v, path)
        else:
            out.add(path)
    return out


def test_config_registry_bidirectional_schema():
    clear_config_cache()
    runtime = as_dict()
    # Flatten runtime config into dotted paths
    runtime_keys = flatten_runtime(runtime)

    registry_text = REGISTRY_PATH.read_text(encoding='utf-8')
    registry_keys = extract_registry_keys(registry_text)

    # Apply ignores
    registry_keys -= IGNORE_REGISTRY_ONLY
    runtime_keys -= IGNORE_RUNTIME_ONLY

    # Compare both directions
    # For registry keys representing maps (e.g., llm.optional_models,
    # llm.reasoning_presets) treat presence of any subkey as satisfied
    satisfied_registry = set()
    for rk in registry_keys:
        if rk in runtime_keys:
            satisfied_registry.add(rk)
            continue
        prefix = rk + '.'
        if any(r.startswith(prefix) for r in runtime_keys):
            satisfied_registry.add(rk)
    missing_in_runtime = sorted(registry_keys - satisfied_registry)

    extra_in_runtime = sorted(
        k for k in (runtime_keys - registry_keys)
        if not any(k.startswith(rk + '.') for rk in registry_keys)
    )

    assert not missing_in_runtime and not extra_in_runtime, (
        'Config registry ↔ runtime mismatch. '
        f'Missing in runtime: {missing_in_runtime} | '
        f'Extra in runtime: {extra_in_runtime}'
    )
