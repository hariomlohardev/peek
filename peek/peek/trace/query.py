"""Query — build depth-limited trace tree (Python only)."""

# ruff: noqa: SIM102, SIM109, F841

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .models import FuncId, FuncNode, TraceGraph


@dataclass
class TraceNode:
    func: FuncNode
    fid: FuncId
    edge: object | None = None  # CallSite that led here
    children: list[TraceNode] = field(default_factory=list)
    depth: int = 0
    is_external: bool = False
    external_label: str | None = None
    is_cycle: bool = False


@dataclass
class TraceTree:
    focal: FuncId
    root: TraceNode
    depth: int = 3
    direction: str = "callees"
    total_nodes: int = 0
    warnings: list[str] = field(default_factory=list)


def trace(
    graph: TraceGraph,
    focal: FuncId,
    depth: int = 3,
    direction: str = "callees",
    cross_file: bool = True,
    show_externals: bool = False,
) -> TraceTree:
    """Build a depth-limited tree from focal.

    direction: "callees" (downstream), "callers" (upstream), "both"
    cross_file: if False, only follow intra-file edges
    show_externals: if False, hide external/builtin leaf nodes
    """
    if depth < 1:
        depth = 1
    if focal not in graph.nodes:
        raise ValueError(f"Focal {focal} not in graph")

    total = 0

    def _build_callees(fid: FuncId, cur_depth: int, path_stack: set[FuncId]) -> TraceNode:
        nonlocal total
        node = graph.nodes[fid]
        tnode = TraceNode(func=node, fid=fid, depth=cur_depth)
        total += 1
        if cur_depth >= depth:
            return tnode
        edges = graph.edges_by_caller.get(fid, [])
        # deduplicate callee_resolved to avoid duplicate branches
        seen: set[FuncId] = set()
        ext_seen: set[str] = set()
        for e in edges:
            if e.callee_resolved:
                if e.callee_resolved in seen:
                    continue
                # cross_file filter
                if not cross_file:
                    try:
                        if e.callee_resolved.file != fid.file:
                            continue
                    except Exception:
                        continue
                if e.callee_resolved in path_stack:
                    # cycle
                    cyc_node = graph.nodes[e.callee_resolved]
                    child = TraceNode(func=cyc_node, fid=e.callee_resolved, edge=e, depth=cur_depth + 1, is_cycle=True)
                    total += 1
                    tnode.children.append(child)
                    seen.add(e.callee_resolved)
                    continue
                if e.callee_resolved not in graph.nodes:
                    continue
                seen.add(e.callee_resolved)
                child = _build_callees(e.callee_resolved, cur_depth + 1, path_stack | {fid})
                child.edge = e
                tnode.children.append(child)
            elif e.is_external:
                if not show_externals:
                    continue
                label = e.external_label or e.callee_raw
                if label in ext_seen:
                    continue
                ext_seen.add(label)
                # create phantom node for external
                from .models import FuncNode as _FN

                phantom_fid = FuncId(file=Path("<external>"), qualname=label)
                phantom_node = _FN(
                    id=phantom_fid,
                    name=label.split(".")[-1],
                    qualname=label,
                    file=Path("<external>"),
                    rel=Path("<external>"),
                    lineno=e.lineno,
                    end_lineno=e.lineno,
                    col=e.col,
                    kind="external",
                )
                child = TraceNode(func=phantom_node, fid=phantom_fid, edge=e, depth=cur_depth + 1, is_external=True, external_label=label)
                total += 1
                tnode.children.append(child)
        return tnode

    def _build_callers(fid: FuncId, cur_depth: int, path_stack: set[FuncId]) -> TraceNode:
        nonlocal total
        node = graph.nodes[fid]
        tnode = TraceNode(func=node, fid=fid, depth=cur_depth)
        total += 1
        if cur_depth >= depth:
            return tnode
        edges = graph.edges_by_callee.get(fid, [])
        seen: set[FuncId] = set()
        for e in edges:
            caller = e.caller
            if caller in seen:
                continue
            if not cross_file and caller.file != fid.file:
                continue
            if caller in path_stack:
                cyc_node = graph.nodes[caller]
                child = TraceNode(func=cyc_node, fid=caller, edge=e, depth=cur_depth + 1, is_cycle=True)
                total += 1
                tnode.children.append(child)
                seen.add(caller)
                continue
            if caller not in graph.nodes:
                continue
            seen.add(caller)
            child = _build_callers(caller, cur_depth + 1, path_stack | {fid})
            child.edge = e
            tnode.children.append(child)
        return tnode

    warnings: list[str] = []
    if direction == "callees":
        root = _build_callees(focal, 0, set())
    elif direction == "callers":
        root = _build_callers(focal, 0, set())
    elif direction == "both":
        # Build callees tree, but also attach caller children at root? For simplicity, build callees and add callers as separate branch
        root = _build_callees(focal, 0, set())
        # attach callers as children at root level with marker?
        # To avoid doubling total logic, just build callers tree and append its children
        caller_root = _build_callers(focal, 0, set())
        # merge caller children into root (with distinct edge)
        # Don't count root twice
        total -= 1  # caller_root counted once extra
        for ch in caller_root.children:
            root.children.append(ch)
    else:
        raise ValueError(direction)

    return TraceTree(focal=focal, root=root, depth=depth, direction=direction, total_nodes=total, warnings=warnings)


def find_focals(graph: TraceGraph, symbol: str, limit: int = 5) -> list[FuncId]:
    # handle file::func syntax
    if "::" in symbol:
        file_part, qual = symbol.split("::", 1)
        file_part = file_part.strip()
        qual = qual.strip()
        candidates: list[FuncId] = []
        for fid, node in graph.nodes.items():
            try:
                rel_str = node.rel.as_posix()
            except Exception:
                rel_str = str(node.rel)
            if (rel_str == file_part or rel_str.endswith(file_part) or fid.file.name == file_part) and (node.qualname == qual or node.name == qual):
                candidates.append(fid)
        if candidates:
            return candidates[:limit]
        # fallback to qual only
        symbol = qual
    elif ":" in symbol and symbol.count(":") == 1:
        # handle single-colon module:func like peek.scanner:scan or peek/scanner.py:scan
        # Avoid Windows drive letter e.g. C:\path
        if not (len(symbol) >= 2 and symbol[1] == ":" and (symbol[2:3] == "\\" or symbol[2:3] == "/")):
            file_part, qual = symbol.rsplit(":", 1)
            file_part = file_part.strip()
            qual = qual.strip()
            if qual.isidentifier() and ("." in file_part or "/" in file_part or "\\" in file_part or file_part.endswith(".py")):
                # normalize module dots to path
                file_part_norm = file_part.replace(".", "/")
                candidates: list[FuncId] = []
                for fid, node in graph.nodes.items():
                    try:
                        rel_str = node.rel.as_posix()
                    except Exception:
                        rel_str = str(node.rel)
                    # check various forms
                    if (
                        rel_str == file_part
                        or rel_str == file_part_norm
                        or rel_str == file_part_norm + ".py"
                        or rel_str.endswith(file_part)
                        or rel_str.endswith(file_part_norm)
                        or rel_str.endswith(file_part_norm + ".py")
                        or fid.file.name == file_part
                        or fid.file.name == file_part_norm.split("/")[-1] + ".py"
                        or rel_str.replace(".py", "") == file_part_norm
                    ) and (node.qualname == qual or node.name == qual):
                        candidates.append(fid)
                if candidates:
                    return candidates[:limit]
                symbol = qual

    # strip file prefix if symbol contains "/" or ".py"
    query = symbol.strip()
    if "/" in query or "\\" in query:
        # maybe user passed path like "peek/scanner.py::scan" already handled; if not, extract last component
        # But for plain symbol with slash, treat as file hint + qual
        # e.g., "peek/scanner.py:scan" -> take after slash
        if "::" not in query and ":" in query:
            query = query.split(":")[-1]
        elif "/" in query:
            query = query.split("/")[-1].split("\\")[-1]

    # Exact qualname match — only for qualified queries (with dot) to avoid hiding bare matches
    if "." in query:
        exact = [fid for fid, n in graph.nodes.items() if n.qualname == query]
        if exact:
            return exact[:limit]
        suffix = [fid for fid, n in graph.nodes.items() if n.qualname.endswith("." + query) or n.qualname == query]
        if suffix:
            return suffix[:limit]
    # Bare name match
    bare = [fid for fid, n in graph.nodes.items() if n.name == query]
    if bare:
        return bare[:limit]
    # Substring in qualname or name
    sub = [fid for fid, n in graph.nodes.items() if query in n.qualname or query in n.name]
    if sub:
        # sort by best match: exact name length, then lineno
        sub_sorted = sorted(sub, key=lambda fid: (len(graph.nodes[fid].qualname), graph.nodes[fid].lineno))
        return sub_sorted[:limit]
    # file substring
    file_sub = [fid for fid, n in graph.nodes.items() if query in n.rel.as_posix() or query in str(n.file)]
    if file_sub:
        return file_sub[:limit]
    return []


def find_by_location(graph: TraceGraph, file_query: str, lineno: int) -> FuncId | None:
    """Find function containing file:line."""
    # Normalize file_query: handle Windows drive letter and slashes, and try both posix and native
    fq_posix = file_query.replace("\\", "/")
    fq_path = None
    fq_resolved = None
    try:
        fq_path = Path(file_query)
        fq_resolved = str(fq_path.resolve()).replace("\\", "/") if fq_path.is_absolute() else None
    except Exception:
        fq_resolved = None

    for fid, node in graph.nodes.items():
        try:
            rel_str = node.rel.as_posix()
        except Exception:
            rel_str = str(node.rel).replace("\\", "/")
        try:
            abs_posix = str(node.file).replace("\\", "/")
        except Exception:
            abs_posix = str(node.file)
        if rel_str == file_query or rel_str == fq_posix or rel_str.endswith(file_query) or rel_str.endswith(fq_posix) or node.file.name == file_query or abs_posix == fq_posix or abs_posix.endswith(fq_posix):
            if node.lineno <= lineno <= node.end_lineno:
                return fid
        if fq_resolved and abs_posix == fq_resolved:
            if node.lineno <= lineno <= node.end_lineno:
                return fid
    # fallback: find closest function in that file before line
    candidates = []
    for fid, node in graph.nodes.items():
        try:
            rel_str = node.rel.as_posix()
        except Exception:
            rel_str = str(node.rel).replace("\\", "/")
        try:
            abs_posix = str(node.file).replace("\\", "/")
        except Exception:
            abs_posix = str(node.file)
        if rel_str == file_query or rel_str == fq_posix or rel_str.endswith(file_query) or rel_str.endswith(fq_posix) or node.file.name == file_query or abs_posix == fq_posix or abs_posix.endswith(fq_posix):
            if node.lineno <= lineno:
                candidates.append((lineno - node.lineno, fid))
        if fq_resolved and abs_posix == fq_resolved:
            if node.lineno <= lineno:
                if not any(c[1] == fid for c in candidates):
                    candidates.append((lineno - node.lineno, fid))
    if candidates:
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]
    return None
