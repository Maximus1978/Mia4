import os
import sys
import json
import time
import re
import inspect

REPORT = {
    "ok": False,
    "error": None,
    "pkg_version": None,
    "llama_cpp_root": None,
    "fmha_symbol_files": [],
    "flash_symbol_files": [],
    "system_info": None,
    "has_fmha_text": False,
    "model_path": None,
    "flash_attn_runtime_flag": None,
    "gen_tokens": None,
    "gen_time_s": None,
    "approx_tps": None,
}

model_path = (
    sys.argv[1] if len(sys.argv) > 1 else os.environ.get("LLAMA_MODEL_PATH")
)
if not model_path:
    REPORT["error"] = "model_path not provided"
    print(json.dumps(REPORT, ensure_ascii=False, indent=2))
    sys.exit(1)
REPORT["model_path"] = model_path

try:
    import llama_cpp
    from llama_cpp import llama_cpp as core
    REPORT["pkg_version"] = getattr(llama_cpp, "__version__", "?")
    root = os.path.dirname(inspect.getfile(llama_cpp))
    REPORT["llama_cpp_root"] = root
    # system info if available
    si_fn = getattr(core, "llama_print_system_info", None)
    if si_fn:
        try:
            REPORT["system_info"] = si_fn().decode(errors="ignore")
        except Exception:
            pass
    # scan for FMHA / FLASH tokens
    fmha_files = []
    flash_files = []
    for dirpath, _, files in os.walk(root):
        for f in files:
            if f.endswith((
                ".c",
                ".cc",
                ".cpp",
                ".h",
                ".cu",
                "CMakeLists.txt",
            )):
                p = os.path.join(dirpath, f)
                try:
                    with open(p, "r", errors="ignore") as fh:
                        txt = fh.read()
                    if "FMHA" in txt:
                        fmha_files.append(p)
                    if re.search(r"FLASH_ATT|FlashAttn", txt):
                        flash_files.append(p)
                except Exception:
                    continue
    REPORT["fmha_symbol_files"] = fmha_files[:25]
    REPORT["flash_symbol_files"] = flash_files[:25]
    REPORT["has_fmha_text"] = bool(fmha_files)
    # runtime model load + short gen
    from llama_cpp import Llama
    t0 = time.time()
    ll = Llama(
        model_path=model_path,
        n_gpu_layers=6,
        logits_all=False,
        embedding=False,
        seed=42,
    )
    # attempt to infer flash attribute
    flash_attr = None
    for cand in ("flash_attn", "fmha", "has_flash_attn"):
        flash_attr = getattr(ll, cand, flash_attr)
    REPORT["flash_attn_runtime_flag"] = flash_attr
    prompt = (
        "Hello. Summarize: artificial intelligence accelerates innovation."
    )  # small prompt
    g0 = time.time()
    out = ll(prompt, max_tokens=16, temperature=0.7, stop=["###"], echo=False)
    g1 = time.time()
    text = out["choices"][0]["text"]
    REPORT["gen_tokens"] = len(text.strip().split())
    REPORT["gen_time_s"] = round(g1 - g0, 4)
    if REPORT["gen_tokens"]:
        REPORT["approx_tps"] = round(
            REPORT["gen_tokens"] / REPORT["gen_time_s"], 3
        )
    REPORT["ok"] = True
except Exception as e:
    REPORT["error"] = f"{type(e).__name__}: {e}"  # keep concise

print(json.dumps(REPORT, ensure_ascii=False, indent=2))
