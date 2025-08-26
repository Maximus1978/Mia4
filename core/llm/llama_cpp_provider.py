"""llama.cpp provider (refactored).

Настройки поступают извне (конфиг + манифест). Внутренних жёстких
дефолтов (temperature, top_p и т.п.) не оставлено. Fake режим —
MIA_LLAMA_FAKE=1.
"""
from __future__ import annotations

import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Iterable

from .provider import ModelProvider, ModelInfo
from .types import GenerationResult
from core.errors import map_exception, validate_error_type
from .exceptions import ModelLoadError, ModelGenerationError
from core.events import (
    emit,
    ModelLoaded,
    ModelLoadFailed,
    ModelUnloaded,
    GenerationStarted,
    GenerationChunk,
    GenerationCompleted,
)

# Важно: не импортируем llama_cpp на уровне модуля, чтобы иметь шанс
# заранее добавить CUDA пути через os.add_dll_directory (иначе ggml_cuda_init
# падает из-за отсутствия cublas* dll в момент первого импорта и GPU помечается
# как недоступный). Делегируем импорт в момент load().
Llama = None  # type: ignore


class LlamaCppProvider(ModelProvider):
    def __init__(
        self,
        model_path: str | Path,
        model_id: str,
        role: str,
        context_length: int,
        n_gpu_layers: int | str,
        temperature: float,
        top_p: float,
        max_output_tokens: int,
        n_threads: int | None = None,
        n_batch: int | None = None,
        fake: bool | None = None,
    ) -> None:
        """Initialize provider.

    n_threads / n_batch are optional CPU tuning overrides forwarded to
    llama.cpp only if not None (letting library select defaults otherwise).
        """
        # Basic params
        self._model_path = Path(model_path)
        self._id = model_id
        self._role = role
        self._ctx = context_length
        self._n_gpu_layers = n_gpu_layers
        self._temperature = temperature
        self._top_p = top_p
        self._max_output_tokens = max_output_tokens
        self._n_threads = n_threads
        self._n_batch = n_batch
        # Mode flags
        env_flag = os.getenv("MIA_LLAMA_FAKE", "0")
        self._fake = bool(int(env_flag)) if fake is None else fake
        # Runtime state
        self._llama: Any | None = None
        self._loaded = False
        self._abort = threading.Event()
        self.last_used: float | None = None

    # control
    def cancel(self) -> None:
        self._abort.set()

    def reset_cancel(self) -> None:
        self._abort.clear()

    # lifecycle
    def load(self) -> None:  # noqa: D401
        if self._loaded:
            return
        t0 = time.time()
        try:
            if not self._model_path.exists() and not self._fake:
                raise ModelLoadError(
                    f"Model file not found: {self._model_path}"
                )
            if self._fake:
                self._loaded = True
            else:
                # Lazy import with CUDA DLL directory injection.
                global Llama  # noqa: PLW0603
                if Llama is None:
                    # Discover candidate CUDA paths from env (prefer explicit
                    # MIA_CUDA_PATH, then CUDA_PATH)
                    cuda_root = (
                        os.getenv("MIA_CUDA_PATH")
                        or os.getenv("CUDA_PATH")
                        or os.getenv("CUDA_HOME")
                    )
                    if cuda_root:
                        candidates = [
                            os.path.join(cuda_root, "bin", "x64"),
                            os.path.join(cuda_root, "bin"),
                        ]
                        for d in candidates:
                            if os.path.isdir(d):
                                try:  # Python 3.8+ only
                                    # add path so CUDA DLLs resolve
                                    os.add_dll_directory(d)  # type: ignore
                                except Exception:  # noqa: BLE001
                                    pass
                    try:
                        from llama_cpp import Llama as _Llama  # type: ignore
                    except Exception as e:  # noqa: BLE001
                        raise ModelLoadError(
                            f"llama_cpp import failed: {e}"
                        ) from e
                    Llama = _Llama  # type: ignore
                if Llama is None:  # safety
                    raise ModelLoadError(
                        "llama_cpp not available after import attempt"
                    )
                params: dict[str, Any] = {
                    "model_path": str(self._model_path),
                    "n_ctx": self._ctx,
                }
                if isinstance(self._n_gpu_layers, int):
                    params["n_gpu_layers"] = self._n_gpu_layers
                elif isinstance(self._n_gpu_layers, str):
                    # 'auto' semantic: запросить полное вынесение слоёв на GPU.
                    # llama.cpp ограничит фактическим числом слоёв, если
                    # значение избыточно.
                    if self._n_gpu_layers.lower() == "auto":
                        params["n_gpu_layers"] = 99999  # большой sentinel
                if self._n_threads is not None:
                    params["n_threads"] = self._n_threads
                if self._n_batch is not None:
                    params["n_batch"] = self._n_batch
                self._llama = Llama(**params)  # type: ignore[call-arg]
                self._loaded = True
            emit(
                ModelLoaded(
                    model_id=self._id,
                    role=self._role,
                    load_ms=int((time.time() - t0) * 1000),
                    revision=None,
                )
            )
        except ValueError as e:  # raw llama.cpp errors (e.g. unknown arch)
            msg = str(e)
            if "unknown model architecture" in msg.lower():
                msg += (
                    " | Hint: model architecture not supported by current "
                    "llama.cpp build. Try a standard Llama/Mistral/Qwen GGUF "
                    "(e.g. *-Q4_K_M.gguf) or upgrade llama-cpp-python."
                )
            wrapped = ModelLoadError(msg)
            code = validate_error_type(map_exception(wrapped, "model.load"))
            emit(
                ModelLoadFailed(
                    model_id=self._id,
                    role=self._role,
                    error_type=code,
                    message=str(wrapped),
                )
            )
            raise wrapped from e
        except ModelLoadError as e:
            code = validate_error_type(map_exception(e, "model.load"))
            emit(
                ModelLoadFailed(
                    model_id=self._id,
                    role=self._role,
                    error_type=code,
                    message=str(e),
                )
            )
            raise

    # inference
    def generate_result(self, prompt: str, **kwargs: Any) -> GenerationResult:
        if not self._loaded:
            self.load()
        max_tokens = int(kwargs.get("max_tokens", self._max_output_tokens))
        temperature = float(kwargs.get("temperature", self._temperature))
        self.reset_cancel()
        request_id = uuid.uuid4().hex
        t0 = time.time()
        emit(
            GenerationStarted(
                request_id=request_id,
                model_id=self._id,
                role=self._role,
                prompt_tokens=len(prompt.split()),
                correlation_id=request_id,
            )
        )
        if self._fake:
            words = prompt.split() or ["empty"]
            out: list[str] = []
            while len(out) < max_tokens and not self._abort.is_set():
                out.extend(words)
            text = " ".join(out[: max_tokens])
            total_ms = int((time.time() - t0) * 1000)
            emit(
                GenerationCompleted(
                    request_id=request_id,
                    model_id=self._id,
                    role=self._role,
                    status="ok",
                    correlation_id=request_id,
                    output_tokens=len(text.split()),
                    latency_ms=total_ms,
                    result_summary={
                        "version": 2,
                        "status": "ok",
                        "usage": {
                            "prompt_tokens": len(prompt.split()),
                            "completion_tokens": len(text.split()),
                        },
                        "timings": {
                            "total_ms": total_ms,
                            "decode_tps": (
                                (len(text.split()) / (total_ms / 1000))
                                if len(text.split()) and total_ms > 0
                                else None
                            ),
                        },
                    },
                )
            )
            self.last_used = time.time()
            return GenerationResult.ok(
                text=text,
                prompt_tokens=len(prompt.split()),
                completion_tokens=len(text.split()),
                total_ms=total_ms,
                model_id=self._id,
                role=self._role,
                request_id=request_id,
            )
        if self._llama is None:
            raise ModelGenerationError("Model not loaded")
        try:
            result = self._llama(  # type: ignore[operator]
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=self._top_p,
                stream=False,
            )
        except Exception as e:  # noqa: BLE001
            code = validate_error_type(map_exception(e, "generation"))
            total_ms = int((time.time() - t0) * 1000)
            emit(
                GenerationCompleted(
                    request_id=request_id,
                    model_id=self._id,
                    role=self._role,
                    status="error",
                    correlation_id=request_id,
                    output_tokens=0,
                    latency_ms=total_ms,
                    error_type=code,
                    message=str(e),
                    result_summary={
                        "version": 2,
                        "status": "error",
                        "error": {"type": code},
                        "timings": {"total_ms": total_ms},
                    },
                )
            )
            raise ModelGenerationError(str(e)) from e
        choices = result.get("choices", [{}])  # type: ignore[index]
        if choices:
            first = choices[0]
            text = first.get("text") or first.get("message", {}).get(
                "content", ""
            )
        else:
            text = ""
        latency_ms = int((time.time() - t0) * 1000)
        emit(
            GenerationCompleted(
                request_id=request_id,
                model_id=self._id,
                role=self._role,
                status="ok",
                correlation_id=request_id,
                output_tokens=len(text.split()),
                latency_ms=latency_ms,
                result_summary={
                    "version": 2,
                    "status": "ok",
                    "usage": {
                        "prompt_tokens": len(prompt.split()),
                        "completion_tokens": len(text.split()),
                    },
                    "timings": {
                        "total_ms": latency_ms,
                        "decode_tps": (
                            (len(text.split()) / (latency_ms / 1000))
                            if len(text.split()) and latency_ms > 0
                            else None
                        ),
                    },
                },
            )
        )
        self.last_used = time.time()
        return GenerationResult.ok(
            text=text,
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(text.split()),
            total_ms=latency_ms,
            model_id=self._id,
            role=self._role,
            request_id=request_id,
        )

    # Backwards compatibility
    def generate(self, prompt: str, **kwargs: Any):  # noqa: D401
        return self.generate_result(prompt, **kwargs)

    def stream(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> Iterable[str]:  # noqa: D401
        if not self._loaded:
            self.load()
        max_tokens = int(kwargs.get("max_tokens", self._max_output_tokens))
        temperature = float(kwargs.get("temperature", self._temperature))
        self.reset_cancel()
        # Unified streaming implementation (fake + real) with events.
        request_id = uuid.uuid4().hex
        t0 = time.time()
        emit(
            GenerationStarted(
                request_id=request_id,
                model_id=self._id,
                role=self._role,
                prompt_tokens=len(prompt.split()),
                correlation_id=request_id,
            )
        )
        produced = 0
        seq = 0
        try:
            if self._fake:
                words = prompt.split() or ["empty"]
                idx = 0
                while produced < max_tokens and not self._abort.is_set():
                    token = words[idx % len(words)] + " "
                    emit(
                        GenerationChunk(
                            request_id=request_id,
                            model_id=self._id,
                            role=self._role,
                            correlation_id=request_id,
                            seq=seq,
                            text=token,
                            tokens_out=produced + 1,
                        )
                    )
                    yield token
                    produced += 1
                    seq += 1
                    idx += 1
            else:
                if self._llama is None:
                    raise ModelGenerationError("Model not loaded")
                for chunk in self._llama(  # type: ignore[operator]
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=self._top_p,
                    stream=True,
                ):
                    if self._abort.is_set():
                        break
                    choice = chunk.get("choices", [{}])[0]
                    # Try multiple possible streaming formats.
                    piece = (
                        choice.get("delta", {}).get("content")
                        or choice.get("text")
                        or choice.get("message", {}).get("content")
                        or ""
                    )
                    if piece:
                        # approximate tokens_out (whitespace split)
                        piece_tokens = len(piece.split()) or 1
                        emit(
                            GenerationChunk(
                                request_id=request_id,
                                model_id=self._id,
                                role=self._role,
                                correlation_id=request_id,
                                seq=seq,
                                text=piece,
                                tokens_out=produced + piece_tokens,
                            )
                        )
                        yield piece
                        produced += piece_tokens
                        seq += 1
        except Exception as e:  # noqa: BLE001
            code = validate_error_type(map_exception(e, "generation"))
            emit(
                GenerationCompleted(
                    request_id=request_id,
                    model_id=self._id,
                    role=self._role,
                    status="error",
                    correlation_id=request_id,
                    output_tokens=produced,
                    latency_ms=int((time.time() - t0) * 1000),
                    error_type=code,
                    message=str(e),
                    result_summary={
                        "version": 2,
                        "status": "error",
                        "error": {"type": code},
                        "timings": {
                            "total_ms": int((time.time() - t0) * 1000)
                        },
                    },
                )
            )
            raise ModelGenerationError(str(e)) from e
        finally:
            self.last_used = time.time()
            if self._abort.is_set():
                emit(
                    GenerationCompleted(
                        request_id=request_id,
                        model_id=self._id,
                        role=self._role,
                        status="error",
                        correlation_id=request_id,
                        output_tokens=produced,
                        latency_ms=int((time.time() - t0) * 1000),
                        error_type=validate_error_type("aborted"),
                        message="cancelled",
                        result_summary={
                            "version": 2,
                            "status": "error",
                            "error": {"type": "aborted"},
                            "timings": {
                                "total_ms": int((time.time() - t0) * 1000)
                            },
                        },
                    )
                )
            else:
                total_ms = int((time.time() - t0) * 1000)
                emit(
                    GenerationCompleted(
                        request_id=request_id,
                        model_id=self._id,
                        role=self._role,
                        status="ok",
                        correlation_id=request_id,
                        output_tokens=produced,
                        latency_ms=total_ms,
                        stop_reason="eos" if produced >= max_tokens else None,
                        result_summary={
                            "version": 2,
                            "status": "ok",
                            "usage": {
                                "prompt_tokens": len(prompt.split()),
                                "completion_tokens": produced,
                            },
                            "timings": {
                                "total_ms": total_ms,
                                "decode_tps": (
                                    (produced / (total_ms / 1000))
                                    if produced and total_ms > 0
                                    else None
                                ),
                            },
                        },
                    )
                )

    def info(self) -> ModelInfo:  # noqa: D401
        caps = getattr(self, "_manifest_capabilities", ("chat",))
        return ModelInfo(
            id=self._id,
            role=self._role,
            capabilities=tuple(caps),
            context_length=self._ctx,
            revision=None,
            metadata={"provider": "llama.cpp", "fake": self._fake},
        )

    def unload(self) -> None:  # noqa: D401
        # For fake mode nothing to release; for real would free context
        was_loaded = self._loaded
        self._llama = None
        self._loaded = False
        if was_loaded:
            idle_seconds = None
            if self.last_used is not None:
                idle_seconds = int(time.time() - self.last_used)
            emit(
                ModelUnloaded(
                    model_id=self._id,
                    role=self._role,
                    reason="manual",  # idle sweep will set reason="idle"
                    idle_seconds=idle_seconds,
                )
            )
