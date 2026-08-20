from __future__ import annotations

import re
from pathlib import Path


def build_dot(ar) -> str:
    lines = ["digraph G {", "  rankdir=LR;", "  node [shape=box, style=filled, fillcolor=\"#232320\", fontcolor=\"#E8E6E3\", color=\"#3A3936\"];"]
    nodes = list(ar.graph.keys())[:15]
    for src in nodes:
        for dst in ar.graph.get(src, set()):
            try:
                s = src.relative_to(ar.root).as_posix()
            except ValueError:
                s = src.name
            try:
                d = dst.relative_to(ar.root).as_posix()
            except ValueError:
                d = dst.name
            lines.append(f'  "{s}" -> "{d}";')
    lines.append("}")
    return "\n".join(lines)


def build_svg(ar) -> str:
    dot = build_dot(ar)
    try:
        import subprocess
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".dot", delete=False) as f:
            f.write(dot)
            fname = f.name
        out = subprocess.check_output(["dot", "-Tsvg", fname], timeout=2).decode()
        return out
    except Exception:
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="400"><rect width="800" height="400" fill="#141413"/><text x="20" y="30" fill="#E8E6E3" font-family="monospace" font-size="12">{dot[:200]}</text></svg>'


def _sanitize_id(rel: str) -> str:
    """Mermaid id must be alphanumeric + underscore, not start with digit."""
    s = re.sub(r"[^a-zA-Z0-9_]", "_", rel)
    if not s:
        s = "node"
    if s[0].isdigit():
        s = "_" + s
    # Collapse consecutive underscores
    s = re.sub(r"__+", "_", s)
    return s


def build_mermaid(ar) -> str:
    """Build Mermaid flowchart (graph TD) from analyzer result."""
    lines: list[str] = ["graph TD"]
    # Collect all nodes (keys + values) for node definitions
    all_nodes: set[Path] = set(ar.graph.keys())
    for deps in ar.graph.values():
        all_nodes.update(deps)
    # Also include keys even if no deps to show isolated nodes
    # Deterministic order by relative posix
    def _rel(p: Path) -> str:
        try:
            return p.relative_to(ar.root).as_posix()
        except ValueError:
            return p.name

    sorted_nodes = sorted(all_nodes, key=lambda p: _rel(p))
    # Map path -> sanitized id, handle collisions
    id_map: dict[Path, str] = {}
    used: set[str] = set()
    for p in sorted_nodes:
        rel = _rel(p)
        base = _sanitize_id(rel)
        cid = base
        counter = 1
        while cid in used:
            counter += 1
            cid = f"{base}_{counter}"
        used.add(cid)
        id_map[p] = cid
        # Use rect style ["label"] — also supports ([label]) but rect is more common
        # Escape quotes in label
        label = rel.replace('"', "'")
        lines.append(f'  {cid}["{label}"]')
    # Edges — limit to first 15 sources like dot for consistency, but include all edges of those
    sources = list(ar.graph.keys())[:15]
    # If graph has many nodes but no edges (e.g., no imports), we already have node lines.
    # For mermaid we also want edges sorted for determinism
    for src in sorted(sources, key=lambda p: _rel(p)):
        dsts = ar.graph.get(src, set())
        src_id = id_map.get(src)
        if not src_id:
            continue
        for dst in sorted(dsts, key=lambda p: _rel(p)):
            dst_id = id_map.get(dst)
            if not dst_id:
                continue
            lines.append(f"  {src_id} --> {dst_id}")
    # If no nodes at all, just return graph TD (still valid mermaid)
    return "\n".join(lines)


def export_graph(ar, format="dot") -> str:
    if format == "dot":
        return build_dot(ar)
    elif format == "svg":
        return build_svg(ar)
    elif format == "html":
        svg = build_svg(ar)
        return f"<!doctype html><meta charset='utf-8'><body style='background:#141413;margin:0'>{svg}</body>"
    elif format == "mermaid":
        return build_mermaid(ar)
    raise ValueError(f"Unknown format {format}")
