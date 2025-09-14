from core.llm import ModelProvider, ModelInfo


def test_model_provider_interface_shape():
    # Ensure abstract interface exposes expected methods.
    for attr in ("load", "generate", "stream", "info"):
        assert hasattr(ModelProvider, attr)


def test_model_info_dataclass():
    info = ModelInfo(
        id="x",
        role="primary",
        capabilities=("chat",),
        context_length=128,
    )
    assert info.id == "x"
    assert "chat" in info.capabilities
