---
title: 2025-09-07 Freeze Preparation
---

## Summary

Items:

* Removed duplicate config registry entries (lightweight id/temperature, ngram.n, collapse.whitespace, ratio_alert duplicate row).
* Deleted obsolete placeholder test `test_postproc_reasoning_split.py` (Harmony migration complete).
* Added pytest markers: realmodel, integration, timeout to silence PytestUnknownMark warnings.
* ADR-0029 accepted: synthetic `ModelLoaded` event when primary already cached (`load_ms=0`).
* Passport attachment path validated for primary model (sampling defaults + hash + version).

Risk Mitigation:

* Registry dedupe keeps bidirectional schema test stable and avoids future drift.
* Synthetic load event prevents flaky model switch tests without expensive reload.

Next (post-freeze) Planned but Deferred:

* ReasoningPresetApplied custom override tagging.
* Perf smoke triple-run snapshot automation.
* RAG store skeleton & events.
