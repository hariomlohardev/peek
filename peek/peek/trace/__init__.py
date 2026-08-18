"""Trace package — Python-only function dependency tree.

Public API:
    build_trace_graph(scan_result) -> TraceGraph
    trace(graph, focal, depth=3, direction="callees", cross_file=True) -> TraceTree
"""

from __future__ import annotations

from .builder import build_trace_graph
from .query import find_by_location, find_focals, trace

__all__ = ["build_trace_graph", "trace", "find_focals", "find_by_location"]
