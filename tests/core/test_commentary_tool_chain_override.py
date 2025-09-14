from core.llm.adapters import HarmonyChannelAdapter


def collect(events_iter):
    return list(events_iter)


def run_adapter(chunks, cfg):
    ad = HarmonyChannelAdapter(cfg)
    out = []
    for ch in chunks:
        out.extend(list(ad.process_chunk(ch)))
    out.extend(list(ad.finalize()))
    return out


def test_tool_chain_override_hash_slice():
    cfg = {
        "model_id": "m1",
        "reasoning": {"max_tokens": 8, "drop_from_history": True},
        "commentary_retention": {
            "mode": "raw_ephemeral",
            "hashed_slice": {"max_chars": 32},
            "raw_ephemeral": {"ttl_seconds": 60},
            "tool_chain": {
                "detect": True,
                "override_mode": "hashed_slice",
                "apply_when": "raw_ephemeral",
                "tag_in_summary": True,
            },
        },
    }
    # Commentary with tool prefix should trigger override
    chunk = (
        "<|start|>assistant<|channel|>commentary<|message|>"
        "[tool:calc status=ok raw={}]<|end|>"
        "<|start|>assistant<|channel|>final<|message|>Answer<|return|>"
    )
    events = run_adapter([chunk], cfg)
    final_ev = next(e for e in events if e.get("type") == "final")
    summary = final_ev.get("commentary_retention_summary")
    assert summary["mode"] == "hashed_slice"
    assert summary.get("applied_override") is True
    assert summary.get("base_mode") == "raw_ephemeral"


def test_tool_chain_override_no_change_when_disabled():
    cfg = {
        "model_id": "m1",
        "reasoning": {"max_tokens": 8, "drop_from_history": True},
        "commentary_retention": {
            "mode": "raw_ephemeral",
            "hashed_slice": {"max_chars": 32},
            "raw_ephemeral": {"ttl_seconds": 60},
            "tool_chain": {
                "detect": False,
                "override_mode": "hashed_slice",
                "apply_when": "raw_ephemeral",
                "tag_in_summary": True,
            },
        },
    }
    chunk = (
        "<|start|>assistant<|channel|>commentary<|message|>"
        "[tool:calc status=ok raw={}]<|end|>"
        "<|start|>assistant<|channel|>final<|message|>Answer<|return|>"
    )
    events = run_adapter([chunk], cfg)
    final_ev = next(e for e in events if e.get("type") == "final")
    summary = final_ev.get("commentary_retention_summary")
    assert summary["mode"] == "raw_ephemeral"  # no override
    assert "applied_override" not in summary


def test_tool_chain_override_any_mode():
    cfg = {
        "model_id": "m1",
        "reasoning": {"max_tokens": 8, "drop_from_history": True},
        "commentary_retention": {
            "mode": "hashed_slice",
            "hashed_slice": {"max_chars": 32},
            "tool_chain": {
                "detect": True,
                "override_mode": "redacted_snippets",
                "apply_when": "any",
                "tag_in_summary": True,
            },
        },
    }
    chunk = (
        "<|start|>assistant<|channel|>commentary<|message|>"
        "[tool:whois status=ok raw={}] secret apiKey=ABCD1234<|end|>"
        "<|start|>assistant<|channel|>final<|message|>Done<|return|>"
    )
    events = run_adapter([chunk], cfg)
    final_ev = next(e for e in events if e.get("type") == "final")
    summary = final_ev.get("commentary_retention_summary")
    assert summary["mode"] == "redacted_snippets"
    assert summary.get("applied_override") is True
    assert summary.get("base_mode") == "hashed_slice"
    assert summary.get("tool_commentary_present") is True
