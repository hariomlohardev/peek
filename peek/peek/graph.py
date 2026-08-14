from __future__ import annotations
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
        import subprocess, tempfile, pathlib
        with tempfile.NamedTemporaryFile(mode="w", suffix=".dot", delete=False) as f:
            f.write(dot); fname = f.name
        out = subprocess.check_output(["dot", "-Tsvg", fname], timeout=2).decode()
        return out
    except Exception:
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="400"><rect width="800" height="400" fill="#141413"/><text x="20" y="30" fill="#E8E6E3" font-family="monospace" font-size="12">{dot[:200]}</text></svg>'

def export_graph(ar, format="dot") -> str:
    if format == "dot":
        return build_dot(ar)
    elif format == "svg":
        return build_svg(ar)
    elif format == "html":
        svg = build_svg(ar)
        return f"<!doctype html><meta charset='utf-8'><body style='background:#141413;margin:0'>{svg}</body>"
    raise ValueError(f"Unknown format {format}")
