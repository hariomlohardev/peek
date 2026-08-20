"""Rendering for trace — rich tree + JSON (Python only, no TUI)."""

# ruff: noqa: SIM105
from __future__ import annotations

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

from .models import TraceGraph
from .query import TraceNode, TraceTree


def _tokens(theme=None) -> dict[str, str]:
    defaults = {
        "accent": "#D4A27F",
        "cyan": "#6CB6FF",
        "muted": "#9A9590",
        "muted2": "#6a6886",
        "ink": "#E8E6E3",
        "green": "#10b981",
        "violet": "#8b5cf6",
        "amber": "#f59e0b",
        "bg": "#0a0a0f",
        "panel": "#14141e",
        "panel2": "#1c1c2a",
        "line": "#23232e",
    }
    try:
        if theme is not None:
            if hasattr(theme, "tokens"):
                merged = dict(defaults)
                merged.update(theme.tokens)  # type: ignore[attr-defined]
                for k, v in defaults.items():
                    if k not in merged or not merged[k]:
                        merged[k] = v
                if not merged.get("amber"):
                    merged["amber"] = defaults["amber"]
                return merged
            if isinstance(theme, dict):
                merged = dict(defaults)
                merged.update(theme)
                for k, v in defaults.items():
                    if k not in merged or not merged[k]:
                        merged[k] = v
                if not merged.get("amber"):
                    merged["amber"] = defaults["amber"]
                return merged
    except Exception:
        pass
    return defaults


def _format_sig(node, theme=None) -> str:  # noqa: ARG001
    params_str = ", ".join(p.format() for p in node.params)
    sig = f"{node.qualname}({params_str})"
    if node.returns:
        sig += f" -> {node.returns}"
    if len(sig) > 90:
        sig = sig[:87] + "..."
    return sig


def _rel_for(node, graph: TraceGraph) -> str:
    try:
        return node.rel.as_posix()
    except Exception:
        try:
            return node.rel.name  # type: ignore[attr-defined]
        except Exception:
            return str(node.file)


def _label_for_trace_node(tnode: TraceNode, graph: TraceGraph, theme=None, *, is_focal: bool = False) -> Text:
    t = _tokens(theme)
    node = tnode.func
    text = Text()
    if tnode.is_external:
        text.append("↗ ", style=f"dim {t['muted']}")
        label = tnode.external_label or node.qualname
        text.append(label, style=t["amber"])
        if tnode.edge:
            text.append(f"  at L{tnode.edge.lineno}", style=f"dim {t['muted2']}")
            if tnode.edge.call_args:
                args_preview = ", ".join(tnode.edge.call_args[:2])
                if len(tnode.edge.call_args) > 2:
                    args_preview += ", …"
                text.append(f"  ({args_preview})", style=f"dim {t['muted']}")
        return text

    if tnode.is_cycle:
        text.append("↺ ", style=f"{t['amber']} bold")

    sig = _format_sig(node, theme)
    sig_style = f"bold {t['accent']}" if is_focal else f"bold {t['ink']}"
    text.append(sig, style=sig_style)
    text.append(f"  [{node.kind}]", style=f"dim italic {t['muted']}")

    rel = _rel_for(node, graph)
    text.append(f"  {rel}:{node.lineno}", style=f"dim {t['muted2']}")

    if tnode.edge:
        e = tnode.edge
        text.append("\n  └─ takes ", style=f"dim {t['muted']}")
        if e.call_args:
            shown = 0
            for arg, src in zip(e.call_args, e.arg_sources, strict=False):  # noqa: B905
                if shown > 0:
                    text.append(", ", style=f"dim {t['muted']}")
                if shown >= 3:
                    text.append("…", style=f"dim {t['muted']}")
                    break
                if src == "PARAM_THROUGH":
                    text.append(arg, style=t["accent"])
                else:
                    text.append(arg, style=f"dim {t['muted']}")
                shown += 1
            # handle more call_args than arg_sources (rare)
            if len(e.call_args) > len(e.arg_sources) and shown < 3:
                for arg in e.call_args[len(e.arg_sources):][: 3 - shown]:
                    if shown > 0:
                        text.append(", ", style=f"dim {t['muted']}")
                    text.append(arg, style=f"dim {t['muted']}")
                    shown += 1
            if len(e.call_args) > 3 and shown <= 3:
                last = text.plain[-1] if text.plain else ""
                if last != "…":
                    text.append(" …", style=f"dim {t['muted']}")
        else:
            text.append("—", style=f"dim {t['muted']}")

        if e.assign_target:
            text.append(f" → {e.assign_target} =", style=f"bold {t['green']}")
        text.append(f" at L{e.lineno}", style=f"dim {t['muted2']}")
        if e.is_await:
            text.append(" await", style=t["violet"])
    return text


# alias for spec compatibility (_label vs _label_for_trace_node)
_label = _label_for_trace_node


def _header_line(trace_tree: TraceTree, graph: TraceGraph, theme=None) -> Text:
    t = _tokens(theme)
    focal = graph.nodes[trace_tree.focal]
    text = Text()
    text.append("peek trace", style=f"bold {t['accent']}")
    text.append(f"  {focal.qualname}", style=f"bold {t['ink']}")
    text.append(f"  —  depth={trace_tree.depth} ", style=f"dim {t['muted']}")
    text.append(f"direction={trace_tree.direction}", style=f"dim {t['muted']}")
    return text


def _meta_line(trace_tree: TraceTree, graph: TraceGraph, theme=None) -> Text:
    t = _tokens(theme)
    focal = graph.nodes[trace_tree.focal]
    files_involved: set = set()
    try:

        def _collect(node: TraceNode) -> None:
            try:
                files_involved.add(node.func.file)
            except Exception:
                pass
            for c in node.children:
                _collect(c)

        _collect(trace_tree.root)
    except Exception:
        pass
    files_involved = {p for p in files_involved if str(p) != "<external>"}
    text = Text()
    text.append(f"{trace_tree.total_nodes} nodes", style=t["green"])
    text.append(f"  •  {len(files_involved)} files", style=f"dim {t['muted']}")
    try:
        rel = focal.rel.as_posix()
    except Exception:
        rel = str(focal.file)
    text.append(f"  •  {rel}:{focal.lineno}", style=f"dim {t['muted2']}")
    return text


def _legend(theme=None) -> Text:
    t = _tokens(theme)
    text = Text()
    text.append("takes", style=f"dim {t['muted']}")
    text.append("  ")
    text.append("■", style=t["accent"])
    text.append(" param", style=f"dim {t['muted']}")
    text.append("  ")
    text.append("→", style=f"bold {t['green']}")
    text.append(" assign", style=f"dim {t['muted']}")
    text.append("  ")
    text.append("await", style=t["violet"])
    text.append("  ")
    text.append("↗", style=t["amber"])
    text.append(" external", style=f"dim {t['muted']}")
    text.append("  ")
    text.append("↺", style=t["amber"])
    text.append(" recursive", style=f"dim {t['muted']}")
    return text


def _file_footnote(trace_tree: TraceTree, graph: TraceGraph, theme=None) -> Text:
    t = _tokens(theme)
    files: set[str] = set()

    def _collect(node: TraceNode) -> None:
        try:
            if str(node.func.file) != "<external>":
                files.add(_rel_for(node.func, graph))
        except Exception:
            pass
        for c in node.children:
            _collect(c)

    _collect(trace_tree.root)
    text = Text()
    if not files:
        return text
    sorted_files = sorted(files)
    text.append("files: ", style=f"dim {t['muted2']}")
    preview = ", ".join(sorted_files[:5])
    text.append(preview, style=f"dim {t['muted']}")
    if len(sorted_files) > 5:
        text.append(f"  +{len(sorted_files) - 5} more", style=f"dim {t['muted2']}")
    return text


def build_rich_tree(trace_tree: TraceTree, graph: TraceGraph, theme=None) -> Tree:
    """Build rich.tree.Tree from TraceTree."""
    t = _tokens(theme)
    root_label = _label_for_trace_node(trace_tree.root, graph, theme, is_focal=True)
    tree = Tree(root_label, guide_style=f"dim {t['muted2']}")

    def _add_children(parent, tnode: TraceNode) -> None:
        for child in tnode.children:
            label = _label_for_trace_node(child, graph, theme, is_focal=False)
            if child.is_external and not child.children:
                parent.add(label)
            elif child.is_cycle:
                label.append("  [recursive]", style=f"dim {t['amber']}")
                parent.add(label)
            else:
                branch = parent.add(label)
                if child.children:
                    _add_children(branch, child)

    _add_children(tree, trace_tree.root)
    return tree


def render_trace(trace_tree: TraceTree, graph: TraceGraph, theme=None, console: Console | None = None) -> Panel:  # noqa: ARG001
    """Render trace tree as a Panel containing rich Tree + summary."""
    t = _tokens(theme)
    header = _header_line(trace_tree, graph, theme)
    meta = _meta_line(trace_tree, graph, theme)
    legend = _legend(theme)
    rich_tree = build_rich_tree(trace_tree, graph, theme)
    footnote = _file_footnote(trace_tree, graph, theme)

    warnings: list[str] = []
    if trace_tree.warnings:
        warnings.extend(trace_tree.warnings)
    if graph.warnings:
        warnings.extend(graph.warnings[:2])

    parts: list = [header, meta, legend, Text(""), rich_tree]
    if footnote.plain:
        parts.extend([Text(""), footnote])
    if warnings:
        warn_text = Text()
        for i, w in enumerate(warnings[:2]):
            if i > 0:
                warn_text.append("  •  ", style=f"dim {t['muted']}")
            warn_text.append(w, style=t["amber"])
        parts.extend([Text(""), warn_text])

    group = Group(*parts)
    title = f"[bold]Trace Tree[/]  [dim]({trace_tree.direction} • depth {trace_tree.depth} • Python only)[/]"
    return Panel(group, title=title, box=box.ROUNDED, border_style=t["accent"], padding=(0, 1))


def trace_to_json(trace_tree: TraceTree, graph: TraceGraph) -> dict:
    """Convert TraceTree to JSON-serializable dict."""

    def _node_to_dict(tnode: TraceNode) -> dict:
        node = tnode.func
        d: dict = {
            "name": node.name,
            "qualname": node.qualname,
            "file": node.rel.as_posix() if hasattr(node.rel, "as_posix") else str(node.rel),
            "lineno": node.lineno,
            "end_lineno": node.end_lineno,
            "kind": node.kind,
            "is_method": node.is_method,
            "class_name": node.class_name,
            "params": [{"name": p.name, "kind": p.kind, "annotation": p.annotation, "default": p.default} for p in node.params],
            "returns": node.returns,
            "is_external": tnode.is_external,
            "is_cycle": tnode.is_cycle,
        }
        if tnode.edge:
            e = tnode.edge
            d["edge"] = {
                "callee_raw": e.callee_raw,
                "callee_name": e.callee_name,
                "lineno": e.lineno,
                "call_args": e.call_args,
                "arg_sources": e.arg_sources,
                "assign_target": e.assign_target,
                "is_await": e.is_await,
                "is_external": e.is_external,
                "external_label": e.external_label,
            }
        d["children"] = [_node_to_dict(c) for c in tnode.children]
        return d

    focal = graph.nodes[trace_tree.focal]
    return {
        "focal": {
            "qualname": focal.qualname,
            "file": focal.rel.as_posix(),
            "lineno": focal.lineno,
            "signature": focal.signature(),
        },
        "direction": trace_tree.direction,
        "depth": trace_tree.depth,
        "total_nodes": trace_tree.total_nodes,
        "tree": _node_to_dict(trace_tree.root),
        "warnings": trace_tree.warnings + graph.warnings,
    }
