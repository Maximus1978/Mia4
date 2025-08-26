"""Autogenerate config documentation (S7).

Scans Pydantic schema classes in core.config.schemas.* and emits a Markdown
summary table to docs/ТЗ/Generated-Config.md. This becomes SSOT snapshot
alongside manually curated Config-Registry.md (which may have richer
narrative). The test will compare to ensure sync.
"""
from __future__ import annotations

import inspect
import importlib
from pathlib import Path
from typing import get_type_hints
import sys

# Ensure root on sys.path before importing pydantic & project modules
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from pydantic import BaseModel
except ImportError as e:  # pragma: no cover - should exist in venv
    raise SystemExit("pydantic not installed in current environment") from e

SCHEMA_MODULES = [
    "core.config.schemas.llm",
    "core.config.schemas.rag",
    "core.config.schemas.perf",
    "core.config.schemas.core",
    "core.config.schemas.observability",
]

OUTPUT_PATH = Path("docs/ТЗ/Generated-Config.md")


def iter_models():
    for mod_name in SCHEMA_MODULES:
        mod = importlib.import_module(mod_name)
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, BaseModel) and obj.__module__ == mod_name:
                yield mod_name, name, obj


def model_fields(cls: type[BaseModel]):
    for fname, field in cls.model_fields.items():  # type: ignore[attr-defined]
        ftype = get_type_hints(cls).get(fname, str(field.annotation))
        default = field.default if field.default is not None else (
            field.default_factory() if field.default_factory else "(required)"
        )
        yield fname, ftype, default, field.description or ""


def generate() -> str:
    lines = [
        "# Generated Config Schemas",
        "",
        "Автогенерировано из Pydantic моделей.",
    ]
    for mod_name, name, cls in iter_models():
        lines.append(f"\n## {name} ({mod_name.split('.')[-1]})\n")
        lines.append("| Field | Type | Default | Notes |")
        lines.append("|-------|------|---------|-------|")
        for fname, ftype, default, note in model_fields(cls):
            type_name = getattr(ftype, "__name__", str(ftype))
            lines.append(
                f"| {fname} | {type_name} | {default} | {note} |"
            )
    return "\n".join(lines) + "\n"


def main():
    # Ensure project root (script parent) on sys.path
    # ROOT already injected above
    content = generate()
    OUTPUT_PATH.write_text(content, encoding="utf-8")
    # Force UTF-8 safe output (Windows console fallback)
    try:
        msg = f"[config-doc] written {OUTPUT_PATH}"
        print(msg.encode("utf-8", "ignore").decode())
    except Exception:  # pragma: no cover
        pass


if __name__ == "__main__":  # pragma: no cover
    main()
