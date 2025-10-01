# 2025-09-18 Legacy Reasoning Sanitization Removal

Status: Shipped

## Summary

Removed obsolete test `test_reasoning_sanitization.py` which validated a former frontend-side reasoning/service marker scrub. Sanitation is now enforced centrally in backend adapter finalize + final SSE frame contract and covered by stream & final-frame tests.

## Rationale

Eliminates redundant pseudo-unit logic that could drift from real sanitation implementation, reducing maintenance noise and false sense of security. Strengthens single-source-of-truth (backend) for INV-CH-ISO.

## Affected Files

- Deleted: `tests/core/test_reasoning_sanitization.py`

## Existing Coverage

- `tests/core/test_no_service_markers_in_stream.py`
- `tests/api/test_generate_final_frame_sanitized.py`
- UI perf / badge tests (indirect: rely on sanitized final text)

## Follow-ups

- Monitor leak metrics (`reasoning_leak_total`, `channel_merge_anomaly_total`) over next week; if 0, proceed to remove any remaining defensive regex scrubs in UI tokens.

## Risks

Low — removal of redundant test only; no production code change.
