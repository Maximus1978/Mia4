from core.llm import ModelProvider, DummyProvider, ModelInfo


def test_dummy_provider_generate_and_stream():
    provider: ModelProvider = DummyProvider(model_id="test-dummy")
    res = provider.generate("hello world")
    assert res.text.lower().startswith("echo: hello")
    tokens = list(provider.stream("hello world"))
    assert len(tokens) >= 2


def test_model_info_dataclass():
    info = ModelInfo(
        id="x",
        role="primary",
        capabilities=("chat",),
        context_length=128,
    )
    assert info.id == "x"
    assert "chat" in info.capabilities
