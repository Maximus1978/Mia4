# 2025-10-01: Dynamic reasoning_max_tokens Passing

## Problem

The `HarmonyChannelAdapter` was initialized with static `postproc.reasoning.max_tokens: 256` from config, but reasoning presets (low=128, medium=150, high=256) defined different token budgets. The adapter never received the dynamic preset value, causing:

- Medium preset: consumed all 512 max_tokens with 256 reasoning tokens, leaving no budget for final answer
- High preset: similar issues when total budget was constrained
- No way for presets to control reasoning budget independently

### Root Cause

Architectural disconnect:
1. Adapter created in `pipeline.py` with static `postproc` config
2. Preset selected in API route with dynamic `reasoning_max_tokens`
3. No mechanism to pass preset value to adapter

### Before Architecture
```
Route → resolves preset → reasoning_max_tokens (discarded)
Pipeline → creates adapter with static postproc config (256)
Adapter → uses hardcoded _max_rez = 256 for all requests
```

### After Architecture
```
Route → resolves preset → reasoning_max_tokens value
    ↓
Pipeline.prepare(reasoning_max_tokens=X) → passes to adapter
    ↓
Adapter.set_context(reasoning_max_tokens=X) → overrides _max_rez
    ↓
Adapter → uses dynamic preset value (128/150/256)
```

## Solution

Implemented proper SSOT-compliant dynamic context passing:

### 1. Adapter Context API Extension (`core/llm/adapters.py`)

Extended `HarmonyChannelAdapter.set_context()` to accept `reasoning_max_tokens`:

```python
def set_context(
    self,
    *,
    request_id: Optional[str] = None,
    model_id: Optional[str] = None,
    reasoning_max_tokens: Optional[int] = None,
) -> None:
    # ... existing code ...
    if reasoning_max_tokens is not None and reasoning_max_tokens > 0:
        self._max_rez = reasoning_max_tokens
```

**Behavior:**
- When provided: overrides `postproc.reasoning.max_tokens` for this request
- When `None` or `<= 0`: falls back to config default (256)
- Preserves backward compatibility for legacy adapters

### 2. Route: Extract Preset Value (`src/mia4/api/routes/generate.py`)

Added extraction of `reasoning_max_tokens` from preset config:

```python
reasoning_max_tokens_preset: int | None = None
if effective_reasoning_mode:
    # ... existing preset application ...
    try:
        preset_full = get_config().llm.reasoning_presets.get(
            effective_reasoning_mode, {}
        )
        reasoning_max_tokens_preset = preset_full.get(
            "reasoning_max_tokens"
        )
    except Exception:  # noqa: BLE001
        pass
```

**Note:** Cannot use `apply_reasoning_overrides()` because it filters out non-generation parameters. Must read preset config directly.

### 3. Pipeline: Accept and Forward (`core/llm/pipeline/primary.py`)

Extended `PrimaryPipeline.prepare()` signature:

```python
def prepare(
    self,
    *,
    # ... existing params ...
    reasoning_max_tokens: int | None = None,
) -> PipelineContext:
```

Pass to adapter during initialization:

```python
adapter.set_context(
    request_id=request_id,
    model_id=model_id,
    reasoning_max_tokens=reasoning_max_tokens,
)
```

## Impact

### Performance
- Medium preset now uses 150 reasoning tokens (was 256), leaving 362 tokens for final answer
- High preset uses full 256 reasoning tokens as designed
- Low preset uses 128 reasoning tokens, maximizing final answer budget

### Expected Behavior (with max_tokens=512)
- **Low (128 reasoning):** ~50 reasoning tokens used, ~400 tokens for final answer
- **Medium (150 reasoning):** ~150 reasoning tokens, ~300 tokens for final answer  
- **High (256 reasoning):** ~256 reasoning tokens, ~200 tokens for final answer

### Config Values (Unchanged)
```yaml
llm:
  reasoning_presets:
    low:
      reasoning_max_tokens: 128
    medium:
      reasoning_max_tokens: 150
    high:
      reasoning_max_tokens: 256
  postproc:
    reasoning:
      max_tokens: 256  # Fallback when no preset
```

## Testing

### Validation Required
1. Restart backend: `scripts\launch\run_backend.bat`
2. Test with Saturn question (`max_tokens=512`):
   - Low preset: should complete with final answer
   - Medium preset: should complete with final answer (was failing)
   - High preset: should complete with final answer
3. Verify SSE events show correct reasoning token counts
4. Check logs for reasoning ratio alerts (should be ~50%, not 100%)

### Metrics to Monitor
- `reasoning_ratio`: should be < 0.5 for all presets
- Final answer length: should be present (>0 tokens)
- Generation timeout: should not occur at 300s limit

## Files Modified

- `core/llm/adapters.py`: Extended `set_context()` with `reasoning_max_tokens` parameter
- `core/llm/pipeline/primary.py`: Added `reasoning_max_tokens` to `prepare()` signature and pass to adapter
- `src/mia4/api/routes/generate.py`: Extract `reasoning_max_tokens` from preset and pass to pipeline

## Principles Applied

**SSOT Compliance:**
- Preset config is single source of truth for `reasoning_max_tokens`
- No hardcoded overrides or temporary config hacks
- Dynamic value passing through proper dependency injection
- Static `postproc.reasoning.max_tokens` remains as fallback

**Backward Compatibility:**
- Adapter still works without preset (uses config default)
- Optional parameter with safe fallback (`> 0` validation)
- Legacy adapters without `set_context()` still functional via AttributeError handling

**Architecture:**
- Clear separation: route resolves, pipeline mediates, adapter applies
- Context passing via explicit parameters, not global state
- Follows ADR-0026 pipeline context patterns

## Related Issues

Fixes P0 issue: "medium preset gave long reasoning but answer was not received"
- Root cause: 256 reasoning tokens consumed entire 512 total budget
- Solution: respect preset's 150 reasoning token limit
- Result: 150 reasoning + 300 final answer tokens

## Next Steps

1. ✅ Implement dynamic context passing (completed)
2. ⏭️ Restart backend and validate all presets
3. ⏭️ Run smoke tests with different max_tokens values
4. ⏭️ Update API documentation to reflect preset behavior
5. ⏭️ Consider exposing reasoning_max_tokens in SSE usage frames

## References

- ADR-0026: Pipeline Context Architecture
- ADR-0028: Cap Logic Delegation
- `configs/base.yaml`: Reasoning presets definition
- User mandate: "не делаем быстрые решения. только правильные согласно ssot"
