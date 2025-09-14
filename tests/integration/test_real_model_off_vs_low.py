import os
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from mia4.api.app import app

REAL_MODEL_ID = os.environ.get("MIA_REAL_MODEL_ID", "gpt-oss-20b-mxfp4")
REAL_MODEL_FILE = (
    Path("models") / "gpt-oss-20b-GGUF" / "gpt-oss-20b-MXFP4.gguf"
)

PROMPTS = [
    "Что такое индекс в базе данных?",
    "В чём разница между потоковой и пакетной обработкой данных?",
]


@pytest.mark.skipif(
    not REAL_MODEL_FILE.exists() or os.environ.get("MIA_REAL_MODEL") != "1",
    reason="real model file missing or MIA_REAL_MODEL flag not set",
)
@pytest.mark.timeout(120)
@pytest.mark.integration
def test_real_model_low_vs_medium_answers(tmp_path):  # noqa: D401
    """Stream answers for reasoning presets low vs medium.

    Goal: compare adjacent reasoning levels (exclude legacy 'off').
    Conditions:
      - Requires real model file present & MIA_REAL_MODEL=1.
    Assertions:
      - Both low & medium produce non-empty final answers.
    - Expect medium reasoning_tokens >= low (warn if lower).
      - On empty final: print full event log for diagnostics and fail.
    """
    client = TestClient(app)

    def _stream(prompt: str, preset: str):
        final = None
        usage = None
        events_log = []  # (event, data_len, sample)
        with client.stream(
            "POST",
            "/generate",
            json={
                "session_id": f"real-{preset}",
                "model": REAL_MODEL_ID,
                "prompt": prompt,
                "overrides": {"reasoning_preset": preset},
            },
        ) as r:
            assert r.status_code == 200
            last = None
            for line in r.iter_lines():
                if not line:
                    continue
                if line.startswith("event: "):
                    last = line.split(": ", 1)[1]
                elif line.startswith("data: "):
                    payload_raw = line[6:]
                    sample = payload_raw[:80]
                    if last == "final":
                        final = json.loads(payload_raw).get("text")
                    elif last == "usage":
                        usage = json.loads(payload_raw)
                    events_log.append((last or "?", len(payload_raw), sample))
                if last == "end":
                    break
        return final or "", usage or {}, events_log

    results = []
    for p in PROMPTS:
        low_text, low_usage, low_log = _stream(p, "low")
        med_text, med_usage, med_log = _stream(p, "medium")
        if not low_text.strip() or not med_text.strip():
            print("[DIAG][low] events:")
            for ev, ln, smp in low_log:
                print(f"  {ev:<10} len={ln} sample={smp}")
            print("[DIAG][medium] events:")
            for ev, ln, smp in med_log:
                print(f"  {ev:<10} len={ln} sample={smp}")
        assert low_text.strip(), "empty final answer (low)"
        assert med_text.strip(), "empty final answer (medium)"
        results.append((p, low_text, med_text, low_usage, med_usage))

    # Reporting & soft heuristic
    for (prompt, low_t, med_t, low_u, med_u) in results:
        low_r = low_u.get("reasoning_tokens")
        med_r = med_u.get("reasoning_tokens")
        print("PROMPT:", prompt)
        print("LOW    reasoning_tokens=", low_r, "chars=", len(low_t))
        print("MEDIUM reasoning_tokens=", med_r, "chars=", len(med_t))
        if (
            med_r is not None
            and low_r is not None
            and med_r < low_r
        ):
            print("[WARN] medium produced fewer reasoning tokens than low")
        if low_t.strip() == med_t.strip():
            print("[NOTE] identical answers low vs medium")
        else:
            diff_ratio = (
                min(len(low_t), len(med_t)) / max(len(low_t), len(med_t))
            )
            if diff_ratio > 0.97:
                print("[INFO] answers very similar (len ratio)")
    # No strict assertions on divergence to avoid flakiness.
