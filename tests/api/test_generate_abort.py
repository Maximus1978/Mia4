import os
import time
from fastapi.testclient import TestClient

from mia4.api.app import app
from core import metrics
from core.events import reset_listeners_for_tests


class _SlowStubProvider:
    def __init__(self):
        self._output = ["hello ", "world "]
        self._idx = 0

    def info(self):  # noqa: D401
        from types import SimpleNamespace
        return SimpleNamespace(
            role="primary",
            metadata={
                "passport_sampling_defaults": {"max_output_tokens": 32}
            },
        )

    def stream(self, prompt: str, **kwargs):  # noqa: D401
        for part in self._output:
            time.sleep(0.05)
            yield part


def test_abort_generation(monkeypatch, tmp_path):  # noqa: D401
    # Minimal config
    cfg_dir = tmp_path / "configs"
    cfg_dir.mkdir(exist_ok=True)
    cfg_dir.joinpath("base.yaml").write_text(
        (
            "modules:\n"
            "  enabled: [llm]\n"
            "llm:\n"
            "  primary:\n"
            "    id: abortModel\n"
            "    max_output_tokens: 64\n"
            "  reasoning_presets:\n"
            "    low: { reasoning_max_tokens: 16, temperature: 0.7, top_p: 0.9 }\n"  # noqa: E501
            "postproc:\n"
            "  enabled: true\n"
            "  reasoning: { max_tokens: 32, drop_from_history: true }\n"  # noqa: E501
        ),
        encoding="utf-8",
    )
    os.environ["MIA_CONFIG_DIR"] = str(cfg_dir)

    # Patch get_model
    from core.llm import factory as factory_mod
    from mia4.api.routes import generate as generate_route

    monkeypatch.setattr(
        factory_mod, "get_model", lambda *a, **k: _SlowStubProvider()
    )
    monkeypatch.setattr(
        generate_route, "get_model", lambda *a, **k: _SlowStubProvider()
    )

    metrics.reset_for_tests()
    reset_listeners_for_tests()
    client = TestClient(app)

    # Start generation (stream) in context manager so we can abort mid-flight
    with client.stream(
        "POST",
        "/generate",
        json={
            "session_id": "s1",
            "model": "abortModel",
            "prompt": "Hello",
            "overrides": {
                "reasoning_preset": "low",
                "dev_per_token_delay_ms": 10,
            },
        },
    ) as r:
        assert r.status_code == 200
        # Note: request_id не отдаётся в явном SSE до финала. Полная
        # проверка abort потребует расширить протокол (будущее). Здесь
        # проверяем endpoint: несуществующий id -> ok False.
        resp = client.post(
            "/generate/abort", json={"request_id": "non-existent"}
        ).json()
        assert resp["ok"] is False
    # Endpoint reachable; глубокий сценарий abort будет добавлен позже.
