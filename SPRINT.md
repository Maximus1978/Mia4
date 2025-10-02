# Current Sprint: Adapter Streaming Integration (2025-10-02)

## 🎯 Sprint Goal
**Fix Harmony channel isolation by integrating adapter.process_chunk() into route streaming loop**

Implement SSOT-compliant solution (Variant A) to ensure reasoning tokens never leak into final_text and session history.

---

## 🔍 Current Status

- **Phase:** Planning → Implementation
- **Last commit:** `5a57fc4` "feat: dynamic reasoning_max_tokens passing + GPU enforcement + timeouts"
- **Branch:** `main`
- **Blocking P0 Issue:** Route does NOT use `adapter.process_chunk()` in streaming loop, causing channel isolation violations

### What We're Fixing

**Problem:** HIGH preset + Saturn question → 256 reasoning tokens generated, but NO final answer delivered to user.

**Root Causes:**
1. Route appends ALL tokens (reasoning + final) to `fragments` without channel filtering (line 658)
2. `adapter.process_chunk()` is NEVER called during streaming
3. Adapter is only invoked at `finalize()`, after streaming completes
4. When `final_text` is empty, reasoning leaks into session history via fallback paths

---

## 🐛 Root Cause Analysis (Detailed)

### Current Flow (BROKEN):
```
Provider generates token
    ↓
Route receives raw token (line 643-660)
    ↓
Route: fragments.append(tok)  ← NO FILTERING!
    ↓
Route: emit SSE "delta" event
    ↓
[Adapter NOT involved in streaming]
    ↓
Route: pipeline.finalize(ctx)
    ↓
Adapter.finalize() processes ALL tokens
    ↓
Too late: reasoning already in fragments
```

### SSOT Violations Identified:

| # | Violation | Location | Impact |
|---|-----------|----------|--------|
| 1 | Route appends all tokens to fragments | `generate.py:658` | Reasoning mixed with final |
| 2 | adapter.process_chunk() never called | `generate.py` streaming loop | No channel filtering |
| 3 | Adapter only used at finalize | `generate.py:941` | Can't prevent leak during stream |

### Evidence from Testing:

**HIGH preset (reasoning_max_tokens=256) + "Saturn rings?" question:**
- ✅ Model generated 256 reasoning tokens
- ✅ e2e latency: 94372ms (~94s)
- ❌ UI showed: `reasoning: none` (not displayed)
- ❌ Final answer: EMPTY
- ❌ Alert: `reasoning: 256/0 (100%)ALERT`

**LOW preset + "как дела?" (immediately after):**
- ❌ UI displayed reasoning about Saturn (from previous HIGH request!)
- ✅ Final answer appeared (but for Saturn, not "как дела?")
- **Conclusion:** Reasoning leaked into session history

---

## ✅ Completed This Sprint

- [x] **Диагностика HIGH preset issue**
  - Traced token flow through route → adapter → finalize
  - Identified that `process_chunk()` is never called
  - Confirmed reasoning reaches `fragments` unfiltered

- [x] **SSOT violations analysis**
  - Violation #1: `fragments.append(tok)` without channel check
  - Violation #2: adapter.process_chunk() not integrated
  - Violation #3: adapter can't enforce isolation during streaming

- [x] **Анализ смешивания prompt между preset**
  - Reasoning saves to history via `fragments` fallback (line 1300/909)
  - `ctx.sanitized_final_text` may contain reasoning when isolation violated
  - Session history contaminates next request in same session

- [x] **Варианты решений (3 options proposed)**
  - Variant A: Full adapter integration (RECOMMENDED)
  - Variant B: Post-finalize sanitation
  - Variant C: Hybrid filter approach

- [x] **Git housekeeping**
  - Committed dynamic reasoning_max_tokens + GPU enforcement
  - Cleaned root directory (moved temp files to tests/temp, scripts/)
  - Pushed to origin/main

---

## 🚧 Active Tasks (Priority Order)

### P0: Implement Variant A (Adapter Streaming Integration)

#### Task 1.1: Create adapter instance before streaming loop
- [ ] Move adapter creation from `finalize` to before streaming starts
- [ ] Pass adapter through context or as local variable
- [ ] Set context (request_id, model_id, reasoning_max_tokens)

#### Task 1.2: Integrate process_chunk() in streaming loop
- [ ] Wrap provider token stream with `adapter.process_chunk(tok)`
- [ ] Iterate over adapter events: `analysis`, `commentary`, `delta`
- [ ] Collect ONLY `delta` events into `fragments`
- [ ] Emit `analysis` events to SSE (don't save to fragments)

#### Task 1.3: Update SSE emission logic
- [ ] Route already has SSE helpers, extend for `analysis` event type
- [ ] Ensure `analysis` events have proper payload (text, tokens count)
- [ ] Test SSE consumer (UI) can handle real-time analysis events

#### Task 1.4: Update finalize() logic
- [ ] Ensure `ctx.sanitized_final_text` is still set by adapter
- [ ] Verify `fragments` now contains ONLY final tokens
- [ ] Remove fallback to `"".join(fragments)` (adapter is SSOT)

#### Task 1.5: Tests & Validation
- [ ] Update `tests/api/test_generate_stream.py` for new flow
- [ ] Add test: reasoning tokens NOT in fragments
- [ ] Add test: SSE analysis events emitted during streaming
- [ ] Add test: final_text is clean (no reasoning markers)
- [ ] Run full pytest suite
- [ ] Manual validation: all 3 presets (low/medium/high)

---

## 📝 Implementation Plan (Variant A)

### Files to Modify:

1. **`src/mia4/api/routes/generate.py`** (PRIMARY)
   - Lines ~365-380: Create adapter BEFORE streaming loop
   - Lines ~550-700: Integrate `adapter.process_chunk()` in loop
   - Lines ~850-870: Keep existing `type=="final"` handler
   - Lines ~900-920: Remove `final_text = "".join(fragments)` fallback

2. **`core/llm/adapters.py`** (NO CHANGES NEEDED)
   - Already implements `process_chunk()` correctly
   - Returns events: `{"type": "analysis|commentary|delta", "text": ...}`

3. **`core/llm/pipeline/primary.py`** (MINOR UPDATE)
   - `finalize()` already uses `ctx.sanitized_final_text` ✅
   - May need to assert `fragments` only contains final tokens

4. **`tests/api/test_generate_stream.py`** (NEW TESTS)
   - Test: analysis events in SSE stream
   - Test: fragments excludes reasoning tokens
   - Test: history contains only final_text

### Pseudo-code for Route Changes:

```python
# BEFORE streaming loop (around line 365)
adapter = HarmonyChannelAdapter(adapter_cfg)
adapter.set_context(
    request_id=request_id,
    model_id=model_id,
    reasoning_max_tokens=reasoning_max_tokens_preset,
)

# INSIDE streaming loop (around line 643-660)
for raw_tok in provider.generate(...):
    # Process through adapter
    for evt in adapter.process_chunk(raw_tok):
        evt_type = evt.get("type")
        
        if evt_type == "analysis":
            # Emit SSE, don't save to fragments
            reasoning_tokens += 1
            yield format_event("analysis", json.dumps({
                "text": evt["text"],
                "request_id": request_id,
            }))
        
        elif evt_type == "commentary":
            # Emit SSE commentary event
            yield format_event("commentary", json.dumps({
                "text": evt["text"],
            }))
        
        elif evt_type == "delta":
            # THIS is final channel - save to fragments
            tok = evt["text"]
            fragments.append(tok)
            tokens_out += 1
            yield format_event("token", json.dumps({
                "text": tok,
                "tokens_out": tokens_out,
            }))

# AT finalize (line ~941) - adapter already processed everything
res = pipeline.finalize(ctx)
final_text = res.final_text  # NO fallback to fragments!
```

---

## 📊 Success Criteria

### Must Pass:
- [ ] HIGH preset + Saturn → reasoning visible in UI, final answer present
- [ ] LOW preset + "как дела?" → NO Saturn reasoning, only current query
- [ ] Session history contains ONLY final_text (no reasoning markers)
- [ ] All pytest suites green (`pytest -q`)
- [ ] UI reasoning block shows analysis in real-time
- [ ] Metrics: `reasoning_leak_total` does NOT increment
- [ ] Metrics: `channel_merge_anomaly_total` stays at 0

### Performance:
- [ ] decode_tps within 5% of baseline (no significant slowdown)
- [ ] First token latency < 2s (analysis should stream immediately)

---

## 📈 Metrics to Monitor

| Metric | Baseline | Target | Alert If |
|--------|----------|--------|----------|
| `reasoning_leak_total` | 0 | 0 | > 0 |
| `channel_merge_anomaly_total` | 0 | 0 | > 0 |
| `decode_tps` | 18-35 tok/s | ±5% | < 17 tok/s |
| `first_token_latency_ms` | < 2000ms | < 2000ms | > 3000ms |

---

## 🚨 Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking streaming loop | Medium | HIGH | Comprehensive tests before merge |
| Performance degradation | Low | Medium | Benchmark before/after |
| SSE format incompatibility | Low | Medium | Update UI consumer if needed |
| Regression in other features | Medium | HIGH | Full test suite + manual validation |

---

## 🔄 Rollback Plan

If implementation fails:
1. `git revert <commit-hash>` to restore pre-integration state
2. Fallback to Variant B (post-finalize sanitation) as temporary fix
3. Document issues in ADR for future attempt

---

## 📚 Reference Documents

- **Root cause analysis:** See "🐛 Root Cause Analysis" section above
- **Architecture:** `AGENTS.md` → "Harmony and Reasoning Quick Reference"
- **Adapter API:** `core/llm/adapters.py` → `HarmonyChannelAdapter.process_chunk()`
- **SSE Contract:** `docs/API.md`
- **Related ADRs:**
  - ADR-0013i: Harmony Channel Separation v2
  - ADR-0014: Postprocessing Reasoning Split
  - ADR-0033: Commentary Retention Policy

---

## ⏭️ Next Steps (Immediate Actions)

1. **Read adapter implementation** (`core/llm/adapters.py:280-350`)
   - Understand event format returned by `process_chunk()`
   - Confirm channel types: `analysis`, `commentary`, `delta`, `tool_call`

2. **Create detailed design doc** (optional, or dive straight into code)
   - Exact line numbers to modify in `generate.py`
   - New variables needed (adapter instance, event counters)
   - SSE payload format for `analysis` events

3. **Start implementation** (once approved)
   - Branch: `feat/adapter-streaming-integration` (or work on main)
   - Commit strategy: small, testable increments
   - Test after each change

---

## 📅 Timeline Estimate

- **Planning & Design:** 1 hour (current)
- **Implementation:** 4-6 hours
  - Route changes: 2-3 hours
  - Test updates: 1-2 hours
  - Debugging: 1 hour buffer
- **Validation:** 1-2 hours
  - Manual testing all presets
  - Full test suite
  - Performance check
- **Documentation:** 1 hour
  - Changelog entry
  - Update SPRINT.md
  - ADR addendum if needed

**Total: 7-10 hours**

---

## 🎓 Lessons Learned (To Document Later)

- Adapter was designed correctly but never integrated into streaming
- Finalize-only approach cannot prevent leaks during streaming phase
- Session history contamination is critical UX bug (confuses users)
- Testing with multiple presets back-to-back reveals isolation bugs

---

## 💬 Notes & Observations

- Model DOES generate proper Harmony channels (`<|channel|>analysis`, `<|channel|>final`)
- Current timeout (300s) is sufficient, not a timing issue
- GPU enforcement working correctly (require_gpu flag validated)
- Dynamic reasoning_max_tokens passing works (adapter receives preset values)
- **Key insight:** The architecture was 90% correct, just missing the streaming integration piece!

---

**Last Updated:** 2025-10-02 (Post-diagnosis, pre-implementation)
**Next Review:** After Variant A implementation complete
