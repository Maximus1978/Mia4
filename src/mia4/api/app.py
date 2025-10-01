"""FastAPI application factory for MIA4 UI/API layer.

Minimal scaffold: /health and /config endpoints.
/generate and /models to be added next iterations.
"""
from __future__ import annotations

import os
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from core.registry.loader import load_manifests
from core.modules.module_manager import get_module_manager
from pathlib import Path
import yaml
from mia4.api.routes.generate import router as generate_router
from core import metrics
from core.config import get_config
import time


def create_app() -> FastAPI:
    app = FastAPI(
        title="MIA4 API",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
    )

    # Dev CORS (UI on :3000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "*",  # dev wildcard (tighten later)
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():  # noqa: D401
        return {"status": "ok"}

    @app.get("/config")
    def config():  # noqa: D401
        ui_mode = os.getenv("MIA_UI_MODE", "user")
        ratio_threshold = None
        primary_payload: dict | None = None
        generation_timeout_s = None
        generation_initial_idle_grace_s = None
        try:
            cfg = get_config()
            llm_conf = getattr(cfg, 'llm', None)
            postproc = (
                getattr(llm_conf, 'postproc', None) if llm_conf else None
            )
            reasoning = None
            if isinstance(postproc, dict):
                reasoning = postproc.get('reasoning')
            elif postproc is not None:
                reasoning = getattr(postproc, 'reasoning', None)
            if isinstance(reasoning, dict):
                ratio_threshold = reasoning.get('ratio_alert_threshold')
            elif reasoning is not None:
                ratio_threshold = getattr(
                    reasoning, 'ratio_alert_threshold', None
                )
            if llm_conf is not None:
                generation_timeout_s = getattr(
                    llm_conf, 'generation_timeout_s', None
                )
                generation_initial_idle_grace_s = getattr(
                    llm_conf, 'generation_initial_idle_grace_s', None
                )
                primary_cfg = getattr(llm_conf, 'primary', None)
                if primary_cfg is not None:
                    primary_payload = {
                        "id": getattr(primary_cfg, 'id', None),
                        "temperature": getattr(
                            primary_cfg, 'temperature', None
                        ),
                        "top_p": getattr(primary_cfg, 'top_p', None),
                        "max_output_tokens": getattr(
                            primary_cfg, 'max_output_tokens', None
                        ),
                        "n_gpu_layers": getattr(
                            primary_cfg, 'n_gpu_layers', None
                        ),
                        "n_threads": getattr(primary_cfg, 'n_threads', None),
                        "n_batch": getattr(primary_cfg, 'n_batch', None),
                    }
        except Exception:  # noqa: BLE001
            ratio_threshold = None
            primary_payload = None
            generation_timeout_s = None
            generation_initial_idle_grace_s = None
        if ratio_threshold is not None:
            try:
                ratio_threshold = float(ratio_threshold)
            except Exception:  # noqa: BLE001
                ratio_threshold = None
        return {
            "ui_mode": ui_mode,
            "reasoning_ratio_threshold": ratio_threshold,
            "generation_timeout_s": generation_timeout_s,
            "generation_initial_idle_grace_s": (
                generation_initial_idle_grace_s
            ),
            "primary": primary_payload,
        }

    @app.get("/presets")
    def presets():  # noqa: D401
        """Expose reasoning presets for UI alignment (read-only)."""
        try:
            cfg = get_config()
            presets = getattr(cfg.llm, "reasoning_presets", {}) or {}
            # Ensure plain dict
            if hasattr(presets, "dict"):
                presets = presets.dict()  # type: ignore[attr-defined]
            return {"reasoning_presets": presets}
        except Exception:  # noqa: BLE001
            return {"reasoning_presets": {}}

    def _load_passport(model_id: str) -> dict | None:
        """Attempt to load model passport file (best-effort)."""
        # convention: models/<model_id>/passport.yaml
        p = Path("models") / model_id / "passport.yaml"
        if not p.exists():
            return None
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            # hash can be added later; keep raw structure minimal
            reasoning_block = data.get("reasoning") or {}
            reasoning_default = reasoning_block.get(
                "default_reasoning_max_tokens"
            )
            return {
                "version": data.get("passport_version"),
                "hash": data.get("hash"),
                "sampling_defaults": data.get("sampling_defaults"),
                "reasoning": {
                    "default_reasoning_max_tokens": reasoning_default
                },
            }
        except Exception:  # noqa: BLE001
            return None

    @app.get("/models")
    def models():  # noqa: D401
        manifests = load_manifests(repo_root=".")
        allowed_roles = {"primary", "lightweight", "secondary"}
        mgr = get_module_manager()
        # IMPORTANT: Do NOT force-load providers here.
        # UI frequently calls /models on startup; loading heavy models here
        # would block or destabilize launch. Only report stub flags for
        # already-loaded providers (best-effort) without triggering new loads.
        primary_stub_by_id: dict[str, bool] = {}
        # Collect stub flags for any already-loaded providers without
        # triggering new heavy loads (query manager llm info())
        try:
            llm_mod = mgr.get("llm")
            loaded_ids = set(llm_mod.info().get("loaded_providers", []))
            for mid in loaded_ids:
                if mid in primary_stub_by_id:
                    continue
                try:
                    # get_provider(mid) should return only if already loaded;
                    # if implementation might load, guard by membership
                    # check above.
                    p = llm_mod.get_provider(mid)
                    mi = p.info()
                    primary_stub_by_id[mid] = bool(
                        (mi.metadata or {}).get("stub")
                    )
                except Exception:  # noqa: BLE001
                    continue
        except Exception:  # noqa: BLE001
            pass
        models_out = []
        for m in manifests.values():
            if m.role not in allowed_roles:
                continue
            if getattr(m, "experimental", False):
                continue
            flags = {
                "experimental": getattr(m, "experimental", False),
                "deprecated": getattr(m, "deprecated", False),
                "alias": False,
                "reusable": True,
                "internal": m.role not in {
                    "primary",
                    "lightweight",
                    "secondary",
                },
                # runtime stub flag (True if provider loaded in stub mode)
                "stub": primary_stub_by_id.get(m.id, False),
            }
            passport = _load_passport(m.id)
            passport_version = passport.get("version") if passport else None
            passport_hash = passport.get("hash") if passport else None
            sampling_defaults = (
                passport.get("sampling_defaults") if passport else None
            ) or {}
            max_out = sampling_defaults.get("max_output_tokens")
            reasoning_default = (
                (passport.get("reasoning") or {}).get(
                    "default_reasoning_max_tokens"
                )
                if passport
                else None
            )
            limits = {
                "max_output_tokens": max_out,
                "context_length": m.context_length,
                "reasoning_max_tokens": reasoning_default,
            }
            models_out.append(
                {
                    "id": m.id,
                    "role": m.role,
                    "capabilities": list(m.capabilities),
                    "context_length": m.context_length,
                    "flags": flags,
                    "passport": passport,
                    "passport_version": passport_version,
                    "passport_hash": passport_hash,
                    "limits": limits,
                    # system prompt hash placeholder (filled later)
                    "system_prompt": None,
                }
            )
        return {"models": models_out}

    # Abort endpoint -------------------------------------------------------
    from mia4.api import abort_registry as _abort_reg  # local import

    @app.post("/generate/abort")
    def abort_generation(payload: dict):  # noqa: D401
        rid = payload.get("request_id") if isinstance(payload, dict) else None
        if not rid:
            return {"ok": False, "error": "missing-request_id"}
        # Record abort initiation time first so stream picks earliest ts
        try:
            _abort_reg.mark_start(str(rid))
        except Exception:  # noqa: BLE001
            pass
        applied = _abort_reg.abort(str(rid))
        # Emit metric even if unknown id so tests observing abort attempts
        # see a counter (legacy compatibility with earlier behavior).
        from core import metrics as _m  # local import to avoid cycle
        try:  # noqa: SIM105
            if applied:
                _m.inc(
                    "generation_cancelled_total",
                    {"model": "unknown", "reason": "user_abort"},
                )
            else:
                _m.inc(
                    "generation_aborted_total",
                    {"model": "unknown", "reason": "unknown-id"},
                )
            # Always emit zero-duration cancel latency sample (ensures
            # histogram presence even if abort is late or unknown id)
            try:
                _m.observe(
                    "cancel_latency_ms", 0.0, {"path": "user_abort"}
                )
            except Exception:  # noqa: BLE001
                pass
        except Exception:  # noqa: BLE001
            pass
        return {"ok": applied, "request_id": rid}

    app.include_router(generate_router)

    # --- Static UI mount (production / fallback) ---
    # If a built frontend exists (chatgpt-design-app/dist), serve it.
    ui_dist = os.path.join(os.getcwd(), "chatgpt-design-app", "dist")
    if os.path.isdir(ui_dist):  # mount only if built
        app.mount("/", StaticFiles(directory=ui_dist, html=True), name="ui")

        @app.get("/", include_in_schema=False)
        def _root_index():  # noqa: D401
            index_path = os.path.join(ui_dist, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            return RedirectResponse("/index.html")

    @app.middleware("http")
    async def _metrics_mw(request: Request, call_next):  # noqa: D401
        start = time.time()
        path = request.url.path
        method = request.method
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            duration_ms = (time.time() - start) * 1000.0
            labels = {"route": path, "method": method}
            metrics.inc("api_request_total", labels)
            metrics.observe("api_request_latency_ms", duration_ms, labels)
            # Errors counting (>=400)
            # If response not set due to internal exception FastAPI
            # will handle, we can't access status here easily.
            # This simplistic version only
            # increments after normal completion; exception paths will be
            # caught by outer handlers later.
            # For MVP acceptable; can extend with custom exception handler.
            # Re-fetch status if available.
            try:  # pragma: no cover - defensive
                status = locals().get("response").status_code  # type: ignore
                if status and status >= 400:
                    metrics.inc(
                        "api_request_errors_total", labels | {"status": status}
                    )
            except Exception:
                pass
    return app


app = create_app()


def main() -> None:  # pragma: no cover
    import uvicorn

    uvicorn.run("mia4.api.app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":  # pragma: no cover
    main()
