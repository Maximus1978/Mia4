from core.llm.adapters import HarmonyChannelAdapter


def _collect(events_iter):
    return list(events_iter)


def test_duplicate_final_in_single_stream_chunk():
    cfg = {
        "model_id": "dup-final-test",
        "reasoning": {"max_tokens": 16, "drop_from_history": True},
        "collapse": {"whitespace": True},
    }
    adapter = HarmonyChannelAdapter(cfg)
    # Single chunk contains two final channel messages back to back
    chunk = (
        "<|start|>assistant<|channel|>final<|message|>Привет! Как дела?<|end|>"
        "<|start|>assistant<|channel|>final<|message|>Привет! Как дела?<|end|>"
    )
    evs = []
    for ev in adapter.process_chunk(chunk):
        evs.append(ev)
    for ev in adapter.finalize():
        evs.append(ev)
    # Only one set of delta tokens should have been emitted
    deltas = [e for e in evs if e.get("type") == "delta"]
    assert len(deltas) == 3  # 'Привет!' 'Как' 'дела?' tokens (approx split)
    final = [e for e in evs if e.get("type") == "final"][0]
    assert final["stats"]["final_tokens"] == 3
