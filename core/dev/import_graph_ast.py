"""AST based import graph builder (Phase 0)."""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, Set


def build_import_graph_ast(root: str | Path = "core") -> Dict[str, Set[str]]:
    root_path = Path(root)
    edges: Dict[str, Set[str]] = {}
    for py in root_path.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        rel_mod = (
            "core." + py.relative_to(root_path).with_suffix("").as_posix()
        ).replace("/", ".")
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    if n.name.startswith("core."):
                        edges.setdefault(rel_mod, set()).add(n.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("core."):
                    edges.setdefault(rel_mod, set()).add(node.module)
    for n in list(edges.keys()):
        for dst in edges[n]:
            edges.setdefault(dst, set())
    return edges


__all__ = ["build_import_graph_ast"]
