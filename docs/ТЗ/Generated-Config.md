# Generated Config Schemas

Автогенерировано из Pydantic моделей.

## LLMConfig (llm)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| primary | PrimaryLLMConfig | PydanticUndefined |  |
| lightweight | LightweightLLMConfig | PydanticUndefined |  |
| optional_models | Dict | PydanticUndefined |  |
| skip_checksum | bool | False |  |
| load_timeout_ms | int | 15000 |  |
| reasoning_presets | Dict | PydanticUndefined |  |

## LightweightLLMConfig (llm)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| id | str | PydanticUndefined |  |
| temperature | float | 0.4 |  |

## OptionalMoEConfig (llm)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| enabled | bool | False |  |
| id | str | None | (required) |  |
| load_mode | str | on_demand |  |
| idle_unload_seconds | int | 300 |  |
| reasoning_default | str | low |  |
| reasoning_overrides | Dict | PydanticUndefined |  |
| timeouts | OptionalMoETimeouts | judge_ms=4000 plan_ms=6000 |  |

## OptionalMoETimeouts (llm)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| judge_ms | int | 4000 |  |
| plan_ms | int | 6000 |  |

## PrimaryLLMConfig (llm)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| id | str | PydanticUndefined |  |
| temperature | float | 0.7 |  |
| top_p | float | 0.9 |  |
| max_output_tokens | int | 1024 |  |
| n_gpu_layers | str | int | auto |  |
| n_threads | int | None | (required) |  |
| n_batch | int | None | (required) |  |

## RAGConfig (rag)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| collection_default | str | memory |  |
| top_k | int | 8 |  |
| hybrid | RAGHybridConfig | weight_semantic=0.6 weight_bm25=0.4 |  |
| normalize | RAGNormalizeConfig | min_score=0.0 max_score=1.0 |  |

## RAGHybridConfig (rag)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| weight_semantic | float | 0.6 |  |
| weight_bm25 | float | 0.4 |  |

## RAGNormalizeConfig (rag)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| min_score | float | 0.0 |  |
| max_score | float | 1.0 |  |

## PerfConfig (perf)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| thresholds | PerfThresholdsConfig | tps_regression_pct=0.12 p95_regression_pct=0.18 p95_ratio_limit=1.3 p95_ratio_regression_pct=0.2 |  |

## PerfThresholdsConfig (perf)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| tps_regression_pct | float | 0.12 |  |
| p95_regression_pct | float | 0.18 |  |
| p95_ratio_limit | float | 1.3 |  |
| p95_ratio_regression_pct | float | 0.2 |  |

## EmbeddingConfig (core)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| id | str | PydanticUndefined |  |

## EmbeddingsConfig (core)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| main | EmbeddingConfig | PydanticUndefined |  |
| fallback | EmbeddingConfig | PydanticUndefined |  |

## EmotionConfig (core)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| model | EmotionModelRef | PydanticUndefined |  |
| fsm | EmotionFSMConfig | PydanticUndefined |  |

## EmotionFSMConfig (core)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| hysteresis_ms | int | 2000 |  |

## EmotionModelRef (core)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| id | str | PydanticUndefined |  |

## ReflectionConfig (core)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| enabled | bool | True |  |
| schedule | ReflectionSchedule | cron='0 3 * * *' |  |

## ReflectionSchedule (core)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| cron | str | 0 3 * * * |  |

## StorageConfig (core)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| paths | StoragePathsConfig | models='models' cache='.cache' data='data' |  |

## StoragePathsConfig (core)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| models | str | models |  |
| cache | str | .cache |  |
| data | str | data |  |

## SystemConfig (core)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| locale | str | ru-RU |  |
| timezone | str | Europe/Moscow |  |

## LoggingConfig (observability)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| level | str | info |  |
| format | str | json |  |

## MetricsConfig (observability)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| export | MetricsExportConfig | prometheus_port=9090 |  |

## MetricsExportConfig (observability)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| prometheus_port | int | 9090 |  |
