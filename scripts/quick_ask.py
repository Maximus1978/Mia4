import sys
import os

# Ensure project root on path when executed directly
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.config import get_config  # noqa: E402
from core.llm.factory import get_model  # noqa: E402

# Usage: python scripts/quick_ask.py "question text"


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/quick_ask.py 'your question'")
        return
    prompt = sys.argv[1]
    cfg = get_config()
    model_id = cfg.llm.primary.id
    provider = get_model(model_id, repo_root='.')
    res = provider.generate(prompt, max_tokens=64)
    print("MODEL:", model_id)
    print("PROMPT:", prompt)
    print("STATUS:", res.status)
    print("TEXT:\n", res.text)
    print("TOKENS:", res.usage)
    print("TIMINGS:", res.timings)


if __name__ == "__main__":
    main()
