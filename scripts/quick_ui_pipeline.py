"""Console replication of /generate streaming pipeline for rapid iteration.

Usage examples (PowerShell):
    python scripts/quick_ui_pipeline.py --prompt "Кратко: зачем нужен индекс?"
    python scripts/quick_ui_pipeline.py -p "Explain indexing" \
            -m gpt-oss-20b-mxfp4 --reasoning medium \
            --temperature 0.7 --top_p 0.95

Features:
    * Mirrors key logic from API /generate route (system prompt injection,
        reasoning marker, preset merge, passport defaults, stop sequences,
        postproc pipeline).
  * Streams tokens to console (optionally suppress per-token output for speed).
    * Shows separated reasoning (if marker or Harmony tags present) and final
        answer + stats.
  * Allows quick experimentation without launching the web UI.

Notes:
  * Does NOT emit events or persist session history.
  * Minimal error handling; intended for local dev only.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import os
import time
from typing import Any, Dict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.config import get_config  # noqa: E402
from core.llm.factory import get_model, apply_reasoning_overrides  # noqa: E402
from core.llm.postproc import process_stream  # noqa: E402


def _build_effective_prompt(
    base_sp: str,
    final_marker: str,
    reasoning_mode: str | None,
    user_prompt: str,
) -> str:
    base_sp_effective = base_sp or ""
    if final_marker not in base_sp_effective and base_sp_effective.strip():
        instr = (
            "\n\n[REASONING SPLIT]\n"
            f"Перед финальным ответом выведите строку {final_marker} "
            "на отдельной строке.\n"
            "Всё до маркера — внутреннее рассуждение. После маркера "
            (
                "дайте только финальный ответ. Не пересказывай и не "
                "повторяй этот блок."
            )
        )
        if reasoning_mode:
            effort_map = {
                "low": "LOW: кратко обозначь шаги.",
                "medium": "MEDIUM: сжатая достаточная цепочка рассуждений.",
                "high": "HIGH: проработай варианты и edge cases без повторов.",
            }
            blk = effort_map.get(reasoning_mode, "")
            if blk:
                instr += (
                    f"\n[LEVEL] {blk}\nReasoning: "
                    f"{reasoning_mode.lower()},\n"
                )
        if not base_sp_effective.endswith("\n"):
            base_sp_effective += "\n"
        base_sp_effective += instr
    return base_sp_effective.strip() + "\n\n" + user_prompt


def run(args: argparse.Namespace) -> int:
    cfg = get_config()
    model_id = args.model or cfg.llm.primary.id
    provider = get_model(model_id, repo_root=".")

    # Passport defaults
    effective_sampling: Dict[str, Any] = {}
    try:
        meta = getattr(provider.info(), "metadata", {}) or {}
        passport_defaults = meta.get("passport_sampling_defaults", {}) or {}
        for k, v in passport_defaults.items():
            if v is not None:
                effective_sampling[k] = v
    except Exception:  # noqa: BLE001
        pass

    # Reasoning preset overrides
    reasoning_mode = args.reasoning
    if reasoning_mode:
        try:
            preset_vals = apply_reasoning_overrides({}, reasoning_mode)
        except KeyError:
            preset_vals = {}
        for k, v in preset_vals.items():
            effective_sampling[k] = v

    # User overrides
    if args.temperature is not None:
        effective_sampling["temperature"] = args.temperature
    if args.top_p is not None:
        effective_sampling["top_p"] = args.top_p
    if args.max_tokens is not None:
        effective_sampling["max_tokens"] = args.max_tokens
    if args.stop:
        effective_sampling["stop"] = args.stop

    # System prompt + marker
    llm_cfg = cfg.llm
    if hasattr(llm_cfg, "system_prompt"):
        base_sp = llm_cfg.system_prompt.get("text", "")
    else:
        base_sp = ""
    try:
        pp_cfg_root = getattr(llm_cfg, "postproc", {})
        final_marker = (
            pp_cfg_root.get("reasoning", {}).get("final_marker")
            if isinstance(pp_cfg_root, dict)
            else None
        ) or "===FINAL==="
    except Exception:  # noqa: BLE001
        final_marker = "===FINAL==="

    # Adjust reasoning max tokens via preset if present
    postproc_cfg = (
        llm_cfg.postproc.copy()
        if hasattr(llm_cfg, "postproc")
        else {"enabled": False}
    )
    if reasoning_mode:
        try:
            preset = llm_cfg.reasoning_presets.get(reasoning_mode, {})
            rmax = preset.get("reasoning_max_tokens")
            if rmax is not None:
                rsec = dict(postproc_cfg.get("reasoning", {}))
                rsec["max_tokens"] = int(rmax)
                postproc_cfg["reasoning"] = rsec
        except Exception:  # noqa: BLE001
            pass

    effective_prompt = _build_effective_prompt(
        base_sp, final_marker, reasoning_mode, args.prompt
    )
    prompt_tokens = len(effective_prompt.split())
    sp_hash = (
        hashlib.sha256(base_sp.encode("utf-8")).hexdigest()[:16]
        if base_sp
        else None
    )

    print(f"MODEL: {model_id}")
    print(f"PROMPT TOKENS (approx words): {prompt_tokens}")
    print(f"SYSTEM_PROMPT_HASH: {sp_hash}")
    print(f"SAMPLING: {effective_sampling}")
    print("--- STREAM START ---")

    t0 = time.time()
    # Filter out marker from stop list if present
    if "stop" in effective_sampling and effective_sampling["stop"]:
        try:
            effective_sampling["stop"] = [
                s for s in effective_sampling["stop"] if s != final_marker
            ]
        except Exception:  # noqa: BLE001
            pass
    raw_stream = provider.stream(effective_prompt, **effective_sampling)
    proc_iter = process_stream(raw_stream, postproc_cfg)

    final_tokens = []
    reasoning_text = None
    reasoning_stats = None
    first_token_ts = None
    tokens_out = 0

    try:
        for evt in proc_iter:
            if evt["type"] == "delta":
                tok = evt["text"]
                tokens_out += 1
                if first_token_ts is None:
                    first_token_ts = time.time()
                    ft_latency = (first_token_ts - t0) * 1000
                    if not args.quiet:
                        print(f"[first_token_latency_ms={ft_latency:.1f}]")
                final_tokens.append(tok)
                if not args.quiet:
                    # print tokens without newline to simulate UI stream
                    print(tok, end="", flush=True)
            elif evt["type"] == "final":
                reasoning_text = evt.get("reasoning_text")
                reasoning_stats = evt.get("stats")
            else:
                continue
    except KeyboardInterrupt:
        print("\n[INTERRUPTED]")
        return 130

    total_latency_ms = (time.time() - t0) * 1000
    decode_tps = (
        (tokens_out / (total_latency_ms / 1000.0)) if tokens_out else 0.0
    )
    final_text = "".join(final_tokens)
    print("\n--- STREAM END ---")
    print(
        (
            "TOKENS_OUT: {t} | TOTAL_LATENCY_MS: {l:.1f} | "
            "DECODE_TPS: {d:.2f}"
        ).format(t=tokens_out, l=total_latency_ms, d=decode_tps)
    )
    if reasoning_stats:
        print("REASONING_STATS:", reasoning_stats)
    if reasoning_text and args.show_reasoning:
        print("\n[REASONING]\n" + reasoning_text.strip())
    print("\n[FINAL ANSWER]\n" + final_text.strip())
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Console /generate replica")
    ap.add_argument("--prompt", "-p", required=True, help="User prompt text")
    ap.add_argument("--model", "-m", help="Model id (defaults primary)")
    ap.add_argument(
        "--reasoning",
        "-r",
        choices=["low", "medium", "high"],
        help="Reasoning preset",
    )
    ap.add_argument("--temperature", type=float)
    ap.add_argument("--top_p", type=float)
    ap.add_argument("--max_tokens", type=int)
    ap.add_argument("--stop", nargs="*", help="Stop sequences")
    ap.add_argument(
        "--show-reasoning",
        action="store_true",
        help="Print reasoning section if present",
    )
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-token output (only final summary)",
    )
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    return run(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
