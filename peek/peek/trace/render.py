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


def _tokens(theme=None) -> dict:
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
    }
    try:
        if theme and hasattr(theme, "tokens"):
            # Merge: theme overrides defaults, but keep defaults for missing keys like amber
            merged = dict(defaults)
            merged.update(theme.tokens)
            # Ensure all defaults present
            for k, v in defaults.items():
                if k not in merged or not merged[k]:
                    merged[k] = v
            return merged
    except Exception:
        pass
    return defaults


def _format_sig(node, theme=None) -> str:
    # name( params ) -> returns
    params_str = ", ".join(p.format() for p in node.params)
    sig = f"{node.qualname}({params_str})"
    if node.returns:
        sig += f" -> {node.returns}"
    # Truncate long sig
    if len(sig) > 90:
        sig = sig[:87] + "..."
    return sig


def _rel_for(node, graph: TraceGraph) -> str:
    try:
        return node.rel.as_posix()
    except Exception:
        try:
            return node.rel.name
        except Exception:
            return str(node.file)


def _label_for_trace_node(tnode: TraceNode, graph: TraceGraph, theme=None) -> Text:
    t = _tokens(theme)
    node = tnode.func
    text = Text()
    # external?
    if tnode.is_external:
        # e.g. external: json.loads
        label = tnode.external_label or node.qualname
        text.append("↗ ", style=f"dim {t['muted']}")
        text.append(label, style=f"{t['amber']}")
        if tnode.edge:
            text.append(f"  at L{tnode.edge.lineno}", style=f"dim {t['muted2']}")
            if tnode.edge.call_args:
                args_preview = ", ".join(tnode.edge.call_args[:2])
                if len(tnode.edge.call_args) > 2:
                    args_preview += ", …"
                text.append(f"  ({args_preview})", style=f"dim {t['muted']}")
        return text

    # Normal func
    # qualname
    if tnode.is_cycle:
        text.append("↺ ", style=f"{t['amber']} bold")
    sig = _format_sig(node, theme)
    # Color qualname part differently? Keep simple
    text.append(sig, style=f"bold {t['ink']}")
    # kind badge
    kind_style = t["cyan"] if node.kind in ("def", "async", "method") else t["violet"]
    text.append(f"  [{node.kind}]", style=f"dim {kind_style}")
    # file + lineno
    rel = _rel_for(node, graph)
    text.append(f"  {rel}:{node.lineno}", style=f"dim {t['muted2']}")
    # docstring hint? Skip
    # Edge info: how its going — show call args and assign
    if tnode.edge:
        e = tnode.edge
        # Show takes
        if e.call_args:
            # Build arg source annotation
            parts = []
            for arg, src in zip(e.call_args, e.arg_sources, strict=False):
                if src == "PARAM_THROUGH":
                    parts.append(f"[green]{arg}[/]")
                elif src == "LITERAL":
                    parts.append(f"[dim]{arg}[/]")
                elif src == "LOCAL_RESULT":
                    parts.append(f"[cyan]{arg}[/]")
                else:
                    parts.append(arg)
            # For rich Text we need plain, but we can use markup later; for Text we add simple
            text.append("\n  └─ takes ", style=f"dim {t['muted']}")
            # Use plain join for Text
            text.append(", ".join(e.call_args[:3]), style=f"dim {t['muted']}")
            if e.assign_target:
                text.append(f" → {e.assign_target} =", style=f" {t['green']}")
            text.append(f" at L{e.lineno}", style=f"dim {t['muted2']}")
            if e.is_await:
                text.append(" await", style=f"dim {t['violet']}")
    return text


def build_rich_tree(trace_tree: TraceTree, graph: TraceGraph, theme=None) -> Tree:
    """Build rich.tree.Tree from TraceTree."""
    t = _tokens(theme)
    root_node = trace_tree.root
    root_label = _label_for_trace_node(root_node, graph, theme)
    # Root style
    tree = Tree(root_label, guide_style=f"dim {t['muted2']}")
    # If depth 0 root has no edge, we still show it expanded

    def _add_children(parent_tree_node, trace_node: TraceNode):
        for child in trace_node.children:
            label = _label_for_trace_node(child, graph, theme)
            # For external, no further children
            if child.is_external and not child.children:
                parent_tree_node.add(label)
            elif child.is_cycle:
                # cycle leaf
                label.append("  [recursive]", style=f"dim {t['amber']}")
                parent_tree_node.add(label)
            else:
                branch = parent_tree_node.add(label)
                if child.children:
                    _add_children(branch, child)

    _add_children(tree, root_node)
    return tree


def render_trace(trace_tree: TraceTree, graph: TraceGraph, theme=None, console: Console | None = None) -> Panel:
    """Render trace tree as a Panel containing rich Tree + summary."""
    t = _tokens(theme)
    # Header summary
    focal = graph.nodes[trace_tree.focal]
    header = Text()
    header.append("peek trace", style=f"bold {t['accent']}")
    header.append(f"  {focal.qualname}", style=f"bold {t['ink']}")
    header.append(f"  —  depth={trace_tree.depth} ", style=f"dim {t['muted']}")
    header.append(f"direction={trace_tree.direction}", style=f"dim {t['muted']}")

    # Warnings
    warnings = []
    if trace_tree.warnings:
        warnings.extend(trace_tree.warnings)
    if graph.warnings:
        warnings.extend(graph.warnings[:2])

    # Build tree
    rich_tree = build_rich_tree(trace_tree, graph, theme)

    # Summary table for file groups
    # Count files involved
    files_involved = set()
    def _collect_files(node: TraceNode):
        try:
            files_involved.add(node.func.file)
        except Exception:
            pass
        for c in node.children:
            _collect_files(c)
    _collect_files(trace_tree.root)
    # Exclude external pseudo
    files_involved = {p for p in files_involved if str(p) != "<external>"}
    summary_line = Text()
    summary_line.append(f"{trace_tree.total_nodes} nodes", style=f"{t['green']}")
    summary_line.append(f"  •  {len(files_involved)} files", style=f"dim {t['muted']}")
    summary_line.append(f"  •  {focal.rel.as_posix()}:{focal.lineno}", style=f"dim {t['muted2']}")
    if warnings:
        summary_line.append(f"  •  {warnings[0]}", style="yellow")

    # Combine
    group = Group(summary_line, Text(""), rich_tree)
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

