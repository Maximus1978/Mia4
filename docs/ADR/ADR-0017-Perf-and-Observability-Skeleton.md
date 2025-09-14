# ADR-0017: Performance & Observability Skeleton

Status: Draft
Date: 2025-08-31

## Context

We need a minimal yet extensible observability layer to (a) quantify latency & throughput, (b) detect regressions relative to a saved baseline, (c) attribute performance characteristics to model passports / configuration changes. Current metrics are ad-hoc.

## Decision

Introduce `PerfCollector` module that ingests Generation* events and maintains rolling windows (fixed-size ring buffers) for:

- first_token_latency_ms
- total_latency_ms
- decode_tps
- reasoning_ratio

Exports aggregated p50/p95 via in-process registry (later Prometheus endpoint). A `BaselineSnapshot` JSON stored under `reports/perf_baseline_snapshot.json` captures median and p95 for representative scenarios (fast model + primary model). A regression guard compares a new snapshot (same scenarios) with allowed deltas defined in config.

## Components

- perf/collector.py (in-memory aggregator)
- perf/baseline.py (run & produce snapshot) script
- perf/guard.py (comparison logic)

## Metrics Naming

`generation_first_token_latency_ms` (hist)  
`generation_decode_tps` (hist)  
`reasoning_ratio` (gauge last + hist)  
`reasoning_ratio_alert_total` (counter)  

## Regression Policy

Allowed delta config keys (example):

```yaml
perf:
  guard:
    first_token_latency_p95_pct: 10   # +10% allowed
    decode_tps_median_pct: -10        # -10% allowed (negative == decrease)
```

Fail build/test suite if exceeded.

## Consequences

- Reproducible perf characterization
- Early detection of silent degradations

## Alternatives Considered

- External APM first (prometheus/grafana). Deferred to keep local iteration fast.

## Testing

- Unit: rolling window aggregation accuracy
- Integration: baseline → guard pass/fail scenarios

## Status Transition

Draft → Accepted after initial collector & guard implemented.
