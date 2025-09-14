from core.llm.adapters import HarmonyChannelAdapter
from core import metrics


def test_tool_chain_override_metric_increment():
    cfg = {
        "model_id": "m1",
        "reasoning": {"max_tokens": 8, "drop_from_history": True},
        "commentary_retention": {
            "mode": "raw_ephemeral",
            "raw_ephemeral": {"ttl_seconds": 30},
            "tool_chain": {
                "detect": True,
                "override_mode": "hashed_slice",
                "apply_when": "raw_ephemeral",
                "tag_in_summary": True,
            },
            "hashed_slice": {"max_chars": 16},
        },
    }
    adapter = HarmonyChannelAdapter(cfg)
    stream = (
        "<|start|>assistant<|channel|>commentary<|message|>"  # tool commentary
        "[tool:calc expr=1+1 status=ok] value=2<|end|>"
        "<|start|>assistant<|channel|>final<|message|>Ans<|return|>"
    )
    list(adapter.process_chunk(stream))
    list(adapter.finalize())
    snap = metrics.snapshot()["counters"]
    prefix = (
        "commentary_retention_override_total{"  # base
        + "from=raw_ephemeral,to=hashed_slice"
    )
    override_keys = [k for k in snap if k.startswith(prefix)]
    assert override_keys, snap
