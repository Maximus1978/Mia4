from __future__ import annotations

from core.llm import ModelProvider


class AliasedProvider(ModelProvider):  # pragma: no cover - thin alias
    """Lightweight alias around an existing provider sharing weights.

    Allows multiple manifest ids referencing same underlying file
    (e.g. judge role reusing primary weights) without reloading model.
    Only overrides metadata; generation delegates to base provider.
    """

    def __init__(
        self,
        base: ModelProvider,
        alias_id: str,
        alias_role: str,
        alias_caps: tuple[str, ...],
    ) -> None:
        self._base = base
        self._alias_id = alias_id
        self._alias_role = alias_role
        self._alias_caps = alias_caps

    # passthroughs
    def load(self) -> None:  # noqa: D401
        self._base.load()

    def generate(self, prompt: str, **kwargs):  # noqa: D401
        return self._base.generate(prompt, **kwargs)

    def stream(self, prompt: str, **kwargs):  # noqa: D401
        return self._base.stream(prompt, **kwargs)

    def info(self):  # noqa: D401
        base_info = self._base.info()
        return type(base_info)(
            id=self._alias_id,
            role=self._alias_role,
            capabilities=self._alias_caps,
            context_length=base_info.context_length,
            revision=base_info.revision,
            metadata=getattr(base_info, "metadata", {}) or {},
        )

    def unload(self) -> None:  # noqa: D401
        # Do not unload base; multiple aliases may reference it.
        return None

    # GPU layering --------------------------------------------------------
    def set_n_gpu_layers(self, value):  # noqa: D401
        setter = getattr(self._base, "set_n_gpu_layers", None)
        if callable(setter):
            return setter(value)
        raise AttributeError("base provider does not support GPU layers")

    def get_effective_n_gpu_layers(self):  # noqa: D401
        getter = getattr(self._base, "get_effective_n_gpu_layers", None)
        if callable(getter):
            return getter()
        return None

    def get_requested_n_gpu_layers(self):  # noqa: D401
        getter = getattr(self._base, "get_requested_n_gpu_layers", None)
        if callable(getter):
            return getter()
        return None
