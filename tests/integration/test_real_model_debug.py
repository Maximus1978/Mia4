import os
import pytest
import sys
from pathlib import Path

from core.llm.factory import get_model

REAL_MODEL_ID = os.environ.get("MIA_REAL_MODEL_ID", "gpt-oss-20b-mxfp4")
REAL_MODEL_PATH = (
    Path("models") / "gpt-oss-20b-GGUF" / "gpt-oss-20b-MXFP4.gguf"
)


@pytest.mark.skipif(
    not REAL_MODEL_PATH.exists(), reason="real model file missing"
)
def test_provider_direct_load_and_generate():
    # Force config to enable llm module if not already loaded
    # Assume base config present; skip if missing
    prov = get_model(REAL_MODEL_ID, repo_root=".")
    prov.load()
    assert getattr(prov, "_loaded", False) is True
    # Minimal generation
    res = prov.generate_result(
        prompt="ping", max_tokens=8, temperature=0.2, top_p=0.95
    )
    assert res.text
    print("DIRECT_DEBUG", {
        "python": sys.version,
        "model_id": REAL_MODEL_ID,
        "supported_params": sorted(
            list(getattr(prov, "_supported_params", set()))
        ),
    })
