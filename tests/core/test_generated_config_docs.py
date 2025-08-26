from pathlib import Path
import hashlib
import subprocess
import sys


def test_generated_config_docs_up_to_date():
    docs_path = Path("docs/ТЗ/Generated-Config.md")
    before = docs_path.read_bytes() if docs_path.exists() else b""
    # Regenerate via script (subprocess to mimic real usage)
    subprocess.check_call([sys.executable, "scripts/generate_config_docs.py"])
    after = docs_path.read_bytes()
    assert after == after  # sanity
    # If content changed compared to repo snapshot, fail with diff hint
    if before != after:
        # Provide quick hash codes to help debug in CI
        b_hash = hashlib.sha256(before).hexdigest()
        a_hash = hashlib.sha256(after).hexdigest()
        raise AssertionError(
            "Generated-Config.md outdated (before "
            f"{b_hash} != after {a_hash}). Commit regenerated file."
        )
