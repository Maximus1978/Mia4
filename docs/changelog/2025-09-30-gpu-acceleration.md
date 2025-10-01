# Changelog 2025-09-30: GPU acceleration hook for LlamaCppProvider

## Summary

Enabled GPU offload for the primary llama.cpp provider by wiring `n_gpu_layers`, `n_threads`, and `n_batch` from configuration. Added an automatic fallback to CPU when CUDA init fails and recorded a dedicated metric to track it. Introduced core unit tests that assert correct parameter propagation and fallback behaviour.

## Details

- Backend: factored `_build_llama_kwargs()` to forward GPU and threading parameters into the llama.cpp constructor; interpreted `n_gpu_layers="auto"` as `-1` (full offload) with automatic conversion to int when numeric text is provided.
- Resilience: on GPU init failure, retry once with `n_gpu_layers=0`, avoid marking the provider as stub, and increment `llama_gpu_fallback_total{model}` for observability.
- Metrics: reused in-memory metrics collector to expose GPU fallback counts so perf dashboards can monitor regressions.
- Tests: added `tests/core/test_llama_provider_gpu.py` covering both direct argument propagation and the fallback flow with `n_gpu_layers="auto"`.

## Risks & Mitigations

- Risk: `-1` auto-offload may still exceed available VRAM. Mitigation: single fallback to CPU + metric for visibility.
- Risk: incorrect type casting on custom configs. Mitigation: safe int parsing with graceful ignore on invalid values.
- Risk: perf regressions if batch/thread parameters are misconfigured. Mitigation: unit coverage plus upcoming perf smoke reruns after deployment.

## Follow-ups

- Capture optimal `n_gpu_layers` per model passport and document in Config Registry.
- Extend perf smoke suite to assert GPU decode throughput and first-token latency envelopes.
- Consider emitting a structured event (e.g. `ModelGpuFallback`) for downstream monitoring once telemetry schema is ready.
