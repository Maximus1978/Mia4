## 2025-09-14 — RAG docs package and events sync

Summary

- Completed RAG documentation package: Architecture, Interfaces, Data Schemas, Events & Metrics, Config (Proposed), Testing & Eval, Security & Privacy, README, Glossary, Normalization & Scoring, Evaluation Dataset.
- Synced canonical events: added RAG.QueryRequested and RAG.IndexRebuilt to `docs/ТЗ/Events.md`; fixed JSON example formatting.
- Merged proposed RAG config keys into `docs/ТЗ/Config-Registry.md` (kept aligned with ADR-0032; acceptance pending).

Notes

- Config keys will be finalized upon ADR-0032 acceptance; until then considered stable-proposed.
- No runtime code paths changed in this slice (docs-only).
