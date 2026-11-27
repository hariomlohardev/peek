"""Import cycles -- groups of files that import each other, directly or not.

`peek graph` draws what imports what. This answers the question that drawing
makes you ask: is there a loop in it, and which files are on it?

The answer comes from the same graph `peek analyze` builds, so it covers every
language that graph covers and shares its limits. Every import statement
counts, including one inside a function or an `if TYPE_CHECKING:` block.

One kind of edge is left out: a file importing the module that contains it
(`pkg/a.py` -> `pkg/__init__.py`). Loading a module always loads its parent
packages first, so that edge exists for every file and says nothing about how
the code is tangled. Counting it would report a cycle for every package whose
`__init__.py` re-exports from its own submodules.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Cycle:
    """One group of files that all reach each other through imports."""

    #: Every file in the group, sorted.
    files: list[Path]
    #: A shortest loop through the group: it starts and ends at ``files[0]``.
    loop: list[Path]


#: Files that stand for the directory they are in.
_PACKAGE_FILES = frozenset({"__init__.py", "mod.rs", "lib.rs", "main.rs"})


def _key(path: Path) -> str:
    return path.as_posix()


def _is_containing_module(src: Path, dst: Path) -> bool:
    """True if *dst* is the module that *src* lives inside."""
    if dst.name in _PACKAGE_FILES:
        return dst.parent in src.parents
    # Rust: the directory a/ may be owned by a.rs next to it.
    return dst.suffix == ".rs" and dst.with_suffix("") in src.parents


def _without_containment(graph: dict[Path, set[Path]]) -> dict[Path, set[Path]]:
    return {
        src: {dst for dst in dsts if not _is_containing_module(src, dst)}
        for src, dsts in graph.items()
    }


def _components(graph: dict[Path, set[Path]]) -> list[list[Path]]:
    """Strongly connected components (Tarjan), without recursion.

    Iterative because a long import chain is ordinary in a large repository and
    must not hit Python's recursion limit.
    """
    index: dict[Path, int] = {}
    low: dict[Path, int] = {}
    on_stack: set[Path] = set()
    stack: list[Path] = []
    components: list[list[Path]] = []
    counter = 0

    def targets(node: Path) -> list[Path]:
        return sorted(graph.get(node, ()), key=_key)

    for root in sorted(graph, key=_key):
        if root in index:
            continue
        index[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        work = [(root, iter(targets(root)))]
        while work:
            node, pending = work[-1]
            for nxt in pending:
                if nxt not in index:
                    index[nxt] = low[nxt] = counter
                    counter += 1
                    stack.append(nxt)
                    on_stack.add(nxt)
                    work.append((nxt, iter(targets(nxt))))
                    break
                if nxt in on_stack:
                    low[node] = min(low[node], index[nxt])
            else:
                work.pop()
                if work:
                    parent = work[-1][0]
                    low[parent] = min(low[parent], low[node])
                if low[node] == index[node]:
                    component = []
                    while True:
                        member = stack.pop()
                        on_stack.discard(member)
                        component.append(member)
                        if member == node:
                            break
                    components.append(component)
    return components


def _shortest_loop(start: Path, members: set[Path], graph: dict[Path, set[Path]]) -> list[Path]:
    """A shortest path from *start* back to itself that stays inside *members*."""
    previous: dict[Path, Path] = {}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nxt in sorted(graph.get(node, ()), key=_key):
            if nxt == start:
                loop = [start]
                while node != start:
                    loop.append(node)
                    node = previous[node]
                loop.append(start)
                loop.reverse()
                return loop
            if nxt in members and nxt not in previous:
                previous[nxt] = node
                queue.append(nxt)
    return [start, start]


def find_cycles(graph: dict[Path, set[Path]]) -> list[Cycle]:
    """Every import cycle in *graph*, smallest group first.

    Files that import each other in several overlapping loops form one group:
    breaking a single loop would not untangle them, so they are reported
    together, with one shortest loop as the example.
    """
    cycles: list[Cycle] = []
    graph = _without_containment(graph)
    for component in _components(graph):
        if len(component) == 1 and component[0] not in graph.get(component[0], ()):
            continue
        files = sorted(component, key=_key)
        cycles.append(Cycle(files=files, loop=_shortest_loop(files[0], set(files), graph)))
    cycles.sort(key=lambda c: (len(c.files), _key(c.files[0])))
    return cycles


def render(cycles: list[Cycle], root: Path, limit: int = 20) -> list[str]:
    """The cycles as lines, `a.py -> b.py -> a.py`."""
    if not cycles:
        return ["No import cycles."]

    def name(path: Path) -> str:
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            return path.name

    noun = "cycle" if len(cycles) == 1 else "cycles"
    lines = [f"{len(cycles)} import {noun}:"]
    for number, cycle in enumerate(cycles[:limit], start=1):
        line = f"{number}. " + " -> ".join(name(p) for p in cycle.loop)
        extra = len(cycle.files) - (len(cycle.loop) - 1)
        if extra > 0:
            line += f"  (+{extra} more in this group)"
        lines.append(line)
    if len(cycles) > limit:
        lines.append(f"... and {len(cycles) - limit} more (raise --limit, or use --json)")
    return lines
