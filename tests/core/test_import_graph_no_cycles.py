from core.dev.import_graph import (
    build_import_graph,
    detect_cycles,
    forbidden_edges,
)

# Layering (future-facing):
#   core.config/events/metrics -> foundation (no inward deps from modules)
#   core.llm/rag/memory/perf/observability -> peers
#   core.modules -> orchestrator; peers must not import it.
# Encodes current + future invariants early.


def test_import_graph_no_cycles_and_forbidden_edges():
    graph = build_import_graph("core")
    cycles = detect_cycles(graph)
    # architecture invariant
    assert not cycles, f"Import cycles detected: {cycles}"
    # Forbidden edges (expand as modules appear)
    rules = [
        # llm isolated from perf (perf only observes events + GenerationResult)
        ("core.llm", "core.perf"),
        ("core.rag", "core.perf"),  # rag isolated from perf
        ("core.memory", "core.perf"),  # memory isolated from perf
        # perf must not reach into internals of peers
        ("core.perf", "core.llm"),
        ("core.perf", "core.rag"),
        ("core.perf", "core.memory"),
        # No module should import the module manager (enforce inversion)
        ("core.llm", "core.modules"),
        ("core.rag", "core.modules"),
        ("core.memory", "core.modules"),
        ("core.perf", "core.modules"),
        ("core.observability", "core.modules"),
    ]
    bad = forbidden_edges(graph, rules)
    # Transitional exceptions (grandfathered until factory layer removed):
    exceptions = {
        ("core.llm.factory", "core.modules.module_manager"),
    }
    bad_effective = [e for e in bad if e not in exceptions]
    assert not bad_effective, (
        f"Forbidden import edges: {bad_effective}"
    )  # keep layering
