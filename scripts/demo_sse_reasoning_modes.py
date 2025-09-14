import os
import tempfile
import pathlib
from fastapi.testclient import TestClient
from mia4.api.app import app
from core.registry.loader import clear_manifest_cache, compute_sha256
from core.metrics import reset_for_tests, snapshot
from core.events import reset_listeners_for_tests

PROMPT = (
    "ЗАДАЧА: кратко объясни что такое индекс в базе данных. "
    "Причины ускорения: структура, селективность, сокращение чтения. "
    "<|start|>assistant<|channel|>analysis<|message|>Индекс — это структура,"  # noqa: E501
    " ускоряющая поиск<|end|><|start|>assistant<|channel|>final<|message|>"
    "Индекс ускоряет выборки за счёт вспомогательной структуры.<|end|>"
)

 
def prep_env(root: pathlib.Path):  # noqa: D401
    clear_manifest_cache()
    models_dir = root / 'models'
    models_dir.mkdir(exist_ok=True)
    model_id = 'demo-model'
    model_file = models_dir / f'{model_id}.bin'
    model_file.write_bytes(b'dummy')
    checksum = compute_sha256(model_file)
    reg_dir = root / 'llm' / 'registry'
    reg_dir.mkdir(parents=True, exist_ok=True)
    manifest_text = (
        f"id: {model_id}\n"
        "family: qwen\n"
        "role: primary\n"
        f"path: models/{model_id}.bin\n"
        "context_length: 2048\n"
        "capabilities: [chat]\n"
        f"checksum_sha256: {checksum}\n"
    )
    (reg_dir / f'{model_id}.yaml').write_text(
        manifest_text, encoding='utf-8'
    )
    cfg_dir = root / 'configs'
    cfg_dir.mkdir(exist_ok=True)
    base_yaml = (
                """modules:
    enabled: [llm]
llm:
    primary:
        id: demo-model
        temperature: 0.7
        top_p: 0.9
        max_output_tokens: 64
        n_gpu_layers: 0
    lightweight:
        id: demo-model
        temperature: 0.5
    reasoning_presets:
        low:
            temperature: 0.6
            top_p: 0.9
            reasoning_max_tokens: 16
        medium:
            temperature: 0.7
            top_p: 0.92
            reasoning_max_tokens: 64
        high:
            temperature: 0.85
            top_p: 0.95
            reasoning_max_tokens: 128
    postproc:
        enabled: true
        reasoning:
            # final_marker removed (Harmony only)
            max_tokens: 256
            drop_from_history: true
            ratio_alert_threshold: 0.9
        ngram:
            n: 3
            window: 64
        collapse:
            whitespace: true
"""
    )
    (cfg_dir / 'base.yaml').write_text(base_yaml, encoding='utf-8')
    os.environ['MIA_CONFIG_DIR'] = str(cfg_dir)
    return model_id

 
def run(mode: str | None):  # noqa: D401
    reset_for_tests()
    reset_listeners_for_tests()
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        model_id = prep_env(root)
        client = TestClient(app)
        overrides = {"max_output_tokens": 64}
        if mode is not None:
            overrides["reasoning_preset"] = mode
        lines = []
        with client.stream('POST', '/generate', json={
            'session_id': 's1',
            'model': model_id,
            'prompt': PROMPT,
            'overrides': overrides,
        }) as r:
            for raw in r.iter_lines():
                if not raw:
                    continue
                lines.append(raw)
                if raw.startswith('event: end'):
                    break
    return lines, snapshot()

 
def _trim(lines: list[str]) -> list[str]:
    keep = {"token", "usage", "final", "end"}
    out: list[str] = []
    last_event = None
    for line in lines:
        if line.startswith("event: "):
            evt = line.split(" ", 1)[1]
            last_event = evt
            if evt in keep:
                out.append(line)
        elif line.startswith("data: ") and last_event in keep:
            out.append(line)
    return out


if __name__ == "__main__":  # pragma: no cover
    lines_low, snap_low = run("low")
    lines_med, snap_med = run("medium")
    lines_high, snap_high = run("high")
    print("--- low SSE (trimmed) ---")
    print("\n".join(_trim(lines_low)))
    print("\n--- medium SSE (trimmed) ---")
    print("\n".join(_trim(lines_med)))
    print("\n--- high SSE (trimmed) ---")
    print("\n".join(_trim(lines_high)))
