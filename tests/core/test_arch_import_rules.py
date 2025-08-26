from core.dev.import_graph_ast import build_import_graph_ast


def test_arch_import_rules_subset():
    graph = build_import_graph_ast("core")
    violations = []
    for src, targets in graph.items():
        for dst in targets:
            if src.startswith("core.llm") and dst.startswith("core.perf"):
                violations.append((src, dst))
            if src.startswith("core.modules") and dst.startswith("scripts"):
                violations.append((src, dst))
    assert not violations, f"Forbidden edges detected: {violations}"
