"""Generate Events Registry Markdown from dataclasses in core.events.

Scans core.events module for dataclass subclasses of BaseEvent and emits a
Markdown table with field lists. This is a lightweight stopgap until a more
formal schema tool is adopted.

Usage (inside venv):
  python scripts/generate_events_registry.py > docs/ТЗ/Generated-Events.md
"""
from __future__ import annotations

import inspect
from dataclasses import is_dataclass, fields
from typing import List, Type, Any

import importlib
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:  # pragma: no cover
    sys.path.insert(0, ROOT)


def load_events_module():  # noqa: D401
    return importlib.import_module("core.events")


def iter_event_classes(mod) -> List[Type[Any]]:  # noqa: D401
    out = []
    for name, obj in inspect.getmembers(mod):
        if name.startswith("_"):
            continue
        if inspect.isclass(obj) and is_dataclass(obj):
            # BaseEvent itself excluded
            if name == "BaseEvent":
                continue
            out.append(obj)
    # stable order
    out.sort(key=lambda c: c.__name__)
    return out


def format_table(classes: List[Type[Any]]) -> str:  # noqa: D401
    lines = [
        "# Generated Events Registry",
        "",
        "| Event | Fields |",
        "|-------|--------|",
    ]
    for cls in classes:
        flds = [f.name for f in fields(cls)]
        lines.append(f"| {cls.__name__} | {', '.join(flds)} |")
    lines.append("")
    lines.append(
        "Generated automatically by scripts/generate_events_registry.py"
    )
    return "\n".join(lines)


def main():  # noqa: D401
    mod = load_events_module()
    classes = iter_event_classes(mod)
    sys.stdout.write(format_table(classes))


if __name__ == "__main__":  # pragma: no cover
    main()
