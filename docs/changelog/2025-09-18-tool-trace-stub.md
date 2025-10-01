# 2025-09-18 Tool Trace Stub

Status: added

## Summary

Added explicit UI stub for tool trace panel when no tool calls occurred. Placeholder contract spec introduced to formalize INV-TOOL-TRACE prior to backend explicit "zero tools" event.

## Changes

- `ToolTracePanel.tsx`: already supported empty state logic; ensured test coverage via existing `tool_trace_panel.spec.tsx`.
- Added placeholder spec `tests/ui/test_tool_trace_stub_placeholder.md` documenting acceptance criteria.
- Changelog entry (this file) marking plan item 8d complete; 8e (contract test for explicit backend absence event) pending.

## Invariants

- INV-TOOL-TRACE (UI half): absence of tool events is explicitly communicated to the developer.

## Follow-ups

- Backend emission of explicit `event: commentary` or dedicated `event: tool_trace` with `status: none` to close the loop.
- Contract test 8e once backend event implemented.
