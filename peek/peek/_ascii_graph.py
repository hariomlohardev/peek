"""ASCII mini-graph — one-liner representation of the import graph."""

from __future__ import annotations

from pathlib import Path


def ascii_graph(graph: dict[Path, set[Path]], ranked, root: Path, max_nodes: int = 5) -> str:
    """Return a one-liner ascii graph like ``cli → scanner → analyzer``.

    Uses ranked order for top nodes; falls back to graph keys.
    Never raises — returns empty string on error.
    """
    try:
        if not graph:
            return ""
        # Prefer ranked order
        if ranked:
            nodes = [r.rel.as_posix() for r in ranked[:max_nodes]]
            # Show chain: A → B → C
            return " → ".join(nodes)
        # Fallback: graph keys
        keys = list(graph.keys())[:max_nodes]
        rels = []
        for k in keys:
            try:
                rels.append(k.relative_to(root).as_posix())
            except ValueError:
                rels.append(k.name)
        return " → ".join(rels)
    except Exception:
        return ""


def ascii_vertical(graph: dict[Path, set[Path]], ranked, root: Path, max_nodes: int = 6) -> str:
    """Vertical variant: each edge on new line ``a\\n │\\n b → c``.

    Kept simple for MVP — ranked list is the graph for most users.
    """
    try:
        if not ranked:
            return ""
        lines: list[str] = []
        for i, r in enumerate(ranked[:max_nodes]):
            lines.append(r.rel.as_posix())
            if i < min(len(ranked), max_nodes) - 1:
                lines.append(" │")
        return "\n".join(lines)
    except Exception:
        return ""
