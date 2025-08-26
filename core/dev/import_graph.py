"""Build import dependency graph for internal modules (S6).

Parses .py files under given root (default core/) collecting edges between
project-internal modules (prefix `core.`). Used in tests to enforce:
  - No cycles between core subpackages.
  - No forbidden edges (architecture constraints).

Simplistic static parsing: looks for lines starting with 'import ' or
'from ' and extracts first module token, trimming trailing segments.
Good enough for guardrail (not an AST heavy tool to keep zero deps).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Set, List, Tuple
import re

IMPORT_RE = re.compile(r"^(?:from|import)\s+([a-zA-Z0-9_.]+)")


def build_import_graph(root: str | Path = "core") -> Dict[str, Set[str]]:
    root_path = Path(root)
    edges: Dict[str, Set[str]] = {}
    for py in root_path.rglob("*.py"):
        if py.name == "__init__.py":
            # still parse for side-effect imports
            pass
        rel_mod = (
            "core." + py.relative_to(root_path).with_suffix("").as_posix()
        ).replace("/", ".")
        with py.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(("#", '"""', "'''")):
                    continue
                m = IMPORT_RE.match(line)
                if not m:
                    continue
                target = m.group(1)
                # Only track internal imports
                if not target.startswith("core."):
                    continue
                # Normalize to top-level module path (without trailing attr)
                tgt = target.split()[0].rstrip(".")
                # Keep full path under core.* (no truncation of depth)
                edges.setdefault(rel_mod, set()).add(tgt)
    # Ensure all nodes present
    for n in list(edges.keys()):
        for m in edges[n]:
            edges.setdefault(m, set())
    return edges


def detect_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    visited: Set[str] = set()
    stack: Set[str] = set()
    cycles: List[List[str]] = []

    def dfs(node: str, path: List[str]):
        if node in stack:
            # cycle found - slice path
            if node in path:
                idx = path.index(node)
                cycles.append(path[idx:] + [node])
            return
        if node in visited:
            return
        visited.add(node)
        stack.add(node)
        for nxt in graph.get(node, []):
            dfs(nxt, path + [nxt])
        stack.remove(node)

    for n in graph:
        if n not in visited:
            dfs(n, [n])
    return cycles


def forbidden_edges(
    graph: Dict[str, Set[str]], rules: List[Tuple[str, str]]
) -> List[Tuple[str, str]]:
    found: List[Tuple[str, str]] = []
    for src, targets in graph.items():
        for dst in targets:
            for a, b in rules:
                if src.startswith(a) and dst.startswith(b):
                    found.append((src, dst))
    return found


__all__ = [
    "build_import_graph",
    "detect_cycles",
    "forbidden_edges",
]
