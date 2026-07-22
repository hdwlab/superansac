"""Shared policy for excluding the removed research-only graph-cut bundle."""

REMOVED_GRAPH_CUT_FILES = {
    "GCoptimization.cpp",
    "GCoptimization.h",
    "LinkedBlockList.cpp",
    "LinkedBlockList.h",
    "block.h",
    "energy.h",
    "graph.cpp",
    "graph.h",
    "maxflow.cpp",
}

RESTRICTED_LICENSE_PHRASES = (
    b"research purposes only",
    b"non-commercial research",
    b"for research use only",
)
