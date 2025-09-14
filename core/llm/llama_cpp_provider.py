"""Minimal llama.cpp provider with deterministic stub fallback.

Summary:
* Lazy, idempotent load guarded by a lock.
* On import / constructor failure uses a deterministic stub (repeats prompt
    words) so tests remain stable without model weights.
* Emits: ModelLoaded / ModelLoadFailed and GenerationStarted /
    GenerationChunk / GenerationCompleted.
* Filters sampling kwargs against llama callable signature; unsupported keys
    listed under sampling.filtered_out.
* Space-only indentation (no tabs) and short lines for lint stability.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any, Dict, Iterable, List, Tuple

from .provider import ModelProvider, ModelInfo
from .types import GenerationResult
from core.errors import map_exception, validate_error_type
from core.events import (
    emit,
    ModelLoaded,
    ModelLoadFailed,
    GenerationStarted,
    GenerationChunk,
    GenerationCompleted,
)


@dataclass(slots=True)
class _State:
    llama: Any | None = None
    loaded: bool = False
    supported_args: set[str] | None = None
    stub: bool = False


class LlamaCppProvider(ModelProvider):
    def __init__(
        self,
        model_path: str | Path,
        model_id: str,
        role: str,
        context_length: int,
        temperature: float | None = None,
        top_p: float | None = None,
        top_k: int | None = None,
        repeat_penalty: float | None = None,
        min_p: float | None = None,
        max_output_tokens: int | None = None,
        n_threads: int | None = None,
        n_batch: int | None = None,
        n_gpu_layers: int | None = None,
    ) -> None:
        self._model_path = str(model_path)
        self._model_id = model_id
        self._role = role
        self._context_length = context_length
        self._base_sampling = {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "repeat_penalty": repeat_penalty,
            "min_p": min_p,
            "max_tokens": max_output_tokens,
            "n_threads": n_threads,
            "n_batch": n_batch,
        }
        if n_gpu_layers is not None:
            self._base_sampling["n_gpu_layers"] = n_gpu_layers
        self._state = _State()
        self._lock = Lock()

    # load -----------------------------------------------------------------
    def load(self) -> None:  # noqa: D401
        if self._state.loaded:
            return
        with self._lock:
            if self._state.loaded:
                return
            start = perf_counter()
            try:
                try:
                    from llama_cpp import Llama  # type: ignore
                except Exception:
                    self._state.stub = True
                    self._state.loaded = True
                    self._loaded = True  # legacy flag
                    emit(
                        ModelLoaded(
                            model_id=self._model_id,
                            role=self._role,
                            load_ms=int((perf_counter() - start) * 1000),
                            revision=None,
                        )
                    )
                    return
                self._state.llama = Llama(
                    model_path=self._model_path,
                    n_ctx=self._context_length,
                    logits_all=False,
                    embedding=False,
                )
                import inspect

                sig = inspect.signature(self._state.llama.__call__)
                self._state.supported_args = set(sig.parameters.keys())
                self._state.loaded = True
                self._loaded = True  # legacy flag
                emit(
                    ModelLoaded(
                        model_id=self._model_id,
                        role=self._role,
                        load_ms=int((perf_counter() - start) * 1000),
                        revision=None,
                    )
                )
            except Exception as e:  # noqa: BLE001
                code = validate_error_type(map_exception(e, "model.load"))
                emit(
                    ModelLoadFailed(
                        model_id=self._model_id,
                        role=self._role,
                        error_type=code,
                        message=str(e)[:400],
                    )
                )
                self._state.stub = True
                self._state.loaded = True
                self._loaded = True  # legacy flag
                emit(
                    ModelLoaded(
                        model_id=self._model_id,
                        role=self._role,
                        load_ms=int((perf_counter() - start) * 1000),
                        revision=None,
                    )
                )

    # helpers --------------------------------------------------------------
    def _filter_sampling(
        self, kwargs: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[str]]:
        supported = self._state.supported_args or set()
        removed: List[str] = []
        out: Dict[str, Any] = {}
        merged = {**self._base_sampling, **kwargs}
        for key, val in merged.items():
            if val is None:
                continue
            if not supported or key in supported:
                out[key] = val
            else:
                removed.append(key)
        return out, removed

    # info -----------------------------------------------------------------
    def info(self) -> ModelInfo:  # noqa: D401
        caps = getattr(self, "_manifest_capabilities", ("chat",))
        meta = {"stub": self._state.stub}
        # Attach passport_version if a passport file exists adjacent to model
        try:
            model_path = Path(self._model_path)
            passport = model_path.parent / "passport.yaml"
            if passport.exists():  # cheap existence check
                meta.setdefault("passport_version", 1)
        except Exception:  # noqa: BLE001
            pass
        return ModelInfo(
            id=self._model_id,
            role=self._role,
            capabilities=tuple(caps),
            context_length=self._context_length,
            revision=None,
            metadata=meta,
        )

    # stub generation ------------------------------------------------------
    def _stub_text(self, prompt: str, max_tokens: int) -> str:
        words = prompt.strip().split()
        if not words:
            return ""
        out: List[str] = []
        i = 0
        while len(out) < max_tokens:
            out.append(words[i % len(words)])
            i += 1
        return " ".join(out)

    # public generation ----------------------------------------------------
    def generate(
        self, prompt: str, request_id: str | None = None, **kwargs: Any
    ) -> GenerationResult:
        self.load()
        self._loaded = self._state.loaded  # legacy flag
        rid = request_id or f"req_{id(self)}_{perf_counter():.0f}"
        sampling, removed = self._filter_sampling(kwargs)
        sampling_meta = dict(sampling)
        if removed:
            sampling_meta["filtered_out"] = removed
        ptoks = len(prompt.split())
        emit(
            GenerationStarted(
                request_id=rid,
                model_id=self._model_id,
                role=self._role,
                prompt_tokens=ptoks,
                sampling=sampling_meta,
            )
        )
        start = perf_counter()
        max_tokens = int(sampling.get("max_tokens") or 128)
        try:
            if self._state.stub or self._state.llama is None:
                text = self._stub_text(prompt, max_tokens) or "ok"
            else:
                llama_obj = self._state.llama
                assert llama_obj is not None
                out = llama_obj(prompt, echo=False, **sampling)
                text = (
                    out.get("choices", [{}])[0].get("text", "")
                    or self._stub_text(prompt, max_tokens)
                    or "ok"
                )
            total = int((perf_counter() - start) * 1000)
            res = GenerationResult.ok(
                text=text,
                prompt_tokens=ptoks,
                completion_tokens=len(text.split()),
                total_ms=total,
                model_id=self._model_id,
                role=self._role,
                request_id=rid,
            )
            emit(
                GenerationCompleted(
                    request_id=rid,
                    model_id=self._model_id,
                    role=self._role,
                    status="ok",
                    correlation_id=rid,
                    output_tokens=res.usage.completion_tokens,
                    latency_ms=res.timings.total_ms,
                    result_summary={"decode_tps": res.timings.decode_tps},
                    stop_reason="stub" if self._state.stub else "eos",
                )
            )
            return res
        except Exception as e:  # noqa: BLE001
            total = int((perf_counter() - start) * 1000)
            code = validate_error_type(map_exception(e, "generation"))
            emit(
                GenerationCompleted(
                    request_id=rid,
                    model_id=self._model_id,
                    role=self._role,
                    status="error",
                    correlation_id=rid,
                    output_tokens=0,
                    latency_ms=total,
                    error_type=code,
                    message=str(e)[:400],
                    result_summary=None,
                    stop_reason="error",
                )
            )
            return GenerationResult.failure(
                err_type=code,
                message=str(e)[:400],
                prompt_tokens=ptoks,
                completion_tokens=0,
                total_ms=total,
                model_id=self._model_id,
                role=self._role,
                request_id=rid,
            )

    # Backward compatible alias used in some tests
    def generate_result(
        self, prompt: str, **kwargs: Any
    ) -> GenerationResult:  # noqa: D401
        return self.generate(prompt, **kwargs)

    def stream(
        self, prompt: str, request_id: str | None = None, **kwargs: Any
    ) -> Iterable[str]:
        # Streaming variant (keeps existing generator code path)
        for part in self._gen(prompt, request_id, True, **kwargs):
            if isinstance(part, str):
                yield part

    # core generation ------------------------------------------------------
    def _gen(  # noqa: D401
        self,
        prompt: str,
        request_id: str | None,
        stream: bool,
        **kwargs: Any,
    ) -> Any:
        self.load()
        self._loaded = self._state.loaded
        rid = request_id or f"req_{id(self)}_{perf_counter():.0f}"
        sampling, removed = self._filter_sampling(kwargs)
        sampling_meta = dict(sampling)
        if removed:
            sampling_meta["filtered_out"] = removed
        ptoks = len(prompt.split())
        emit(
            GenerationStarted(
                request_id=rid,
                model_id=self._model_id,
                role=self._role,
                prompt_tokens=ptoks,
                sampling=sampling_meta,
            )
        )
        start = perf_counter()
        max_tokens = int(sampling.get("max_tokens") or 128)
        try:
            if self._state.stub or self._state.llama is None:
                # Stream deterministic stub token-by-token
                full = self._stub_text(prompt, max_tokens)
                tokens = full.split()
                acc: List[str] = []
                for idx, tok in enumerate(tokens):
                    acc.append(tok)
                    piece = tok + (" " if idx < len(tokens) - 1 else "")
                    emit(
                        GenerationChunk(
                            request_id=rid,
                            model_id=self._model_id,
                            role=self._role,
                            correlation_id=rid,
                            seq=idx,
                            text=piece,
                            tokens_out=len(acc),
                        )
                    )
                    yield piece
                total = int((perf_counter() - start) * 1000)
                emit(
                    GenerationCompleted(
                        request_id=rid,
                        model_id=self._model_id,
                        role=self._role,
                        status="ok",
                        correlation_id=rid,
                        output_tokens=len(tokens),
                        latency_ms=total,
                        result_summary=None,
                        stop_reason="stub",
                    )
                )
                return
            llama_obj = self._state.llama
            assert llama_obj is not None
            seq = 0
            acc: List[str] = []
            for token in llama_obj(prompt, stream=True, **sampling):
                if not isinstance(token, dict):
                    continue
                piece = token.get("choices", [{}])[0].get("text", "")
                if not piece:
                    continue
                acc.append(piece)
                emit(
                    GenerationChunk(
                        request_id=rid,
                        model_id=self._model_id,
                        role=self._role,
                        correlation_id=rid,
                        seq=seq,
                        text=piece,
                        tokens_out=len(acc),
                    )
                )
                seq += 1
                yield piece
            total = int((perf_counter() - start) * 1000)
            emit(
                GenerationCompleted(
                    request_id=rid,
                    model_id=self._model_id,
                    role=self._role,
                    status="ok",
                    correlation_id=rid,
                    output_tokens=len(acc),
                    latency_ms=total,
                    result_summary=None,
                    stop_reason="eos",
                )
            )
        except Exception as e:  # noqa: BLE001
            total = int((perf_counter() - start) * 1000)
            code = validate_error_type(map_exception(e, "generation"))
            emit(
                GenerationCompleted(
                    request_id=rid,
                    model_id=self._model_id,
                    role=self._role,
                    status="error",
                    correlation_id=rid,
                    output_tokens=0,
                    latency_ms=total,
                    error_type=code,
                    message=str(e)[:400],
                    result_summary=None,
                    stop_reason="error",
                )
            )
            if stream:
                return
            fail = GenerationResult.failure(
                err_type=code,
                message=str(e)[:400],
                prompt_tokens=ptoks,
                completion_tokens=0,
                total_ms=total,
                model_id=self._model_id,
                role=self._role,
                request_id=rid,
            )
            return fail
            seq = 0
            acc: List[str] = []
            for token in llama_obj(prompt, stream=True, **sampling):
                if not isinstance(token, dict):
                    continue
                piece = token.get("choices", [{}])[0].get("text", "")
                if not piece:
                    continue
                acc.append(piece)
                emit(
                    GenerationChunk(
                        request_id=rid,
                        model_id=self._model_id,
                        role=self._role,
                        correlation_id=rid,
                        seq=seq,
                        text=piece,
                        tokens_out=len(acc),
                    )
                )
                seq += 1
                yield piece
            total = int((perf_counter() - start) * 1000)
            emit(
                GenerationCompleted(
                    request_id=rid,
                    model_id=self._model_id,
                    role=self._role,
                    status="ok",
                    correlation_id=rid,
                    output_tokens=len(acc),
                    latency_ms=total,
                    result_summary=None,
                    stop_reason="eos",
                )
            )
        except Exception as e:  # noqa: BLE001
            total = int((perf_counter() - start) * 1000)
            code = validate_error_type(map_exception(e, "generation"))
            emit(
                GenerationCompleted(
                    request_id=rid,
                    model_id=self._model_id,
                    role=self._role,
                    status="error",
                    correlation_id=rid,
                    output_tokens=0,
                    latency_ms=total,
                    error_type=code,
                    message=str(e)[:400],
                    result_summary=None,
                    stop_reason="error",
                )
            )
            if stream:
                return
            fail = GenerationResult.failure(
                err_type=code,
                message=str(e)[:400],
                prompt_tokens=ptoks,
                completion_tokens=0,
                total_ms=total,
                model_id=self._model_id,
                role=self._role,
                request_id=rid,
            )
            return fail

    # unload --------------------------------------------------------------
    def unload(self) -> None:  # noqa: D401
        if self._state.llama is not None:
            try:
                del self._state.llama  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass
        self._state.llama = None
        self._state.loaded = False
        self._state.supported_args = None


__all__ = ["LlamaCppProvider"]

