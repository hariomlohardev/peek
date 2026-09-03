"""Why is this package here? — trace an external dependency back to the code.

`peek graph` answers "what imports what" between the repo's own files.
This answers the question you ask when a dependency shows up in a lockfile
and nobody remembers asking for it: which file imports it, and what leads
there from the outside.
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path

# The top-level name of an import, which is what a package is called in a
# requirements file. `from rich.console import Console` is a use of `rich`.
_PY_IMPORT_RE = re.compile(
    r"^[ \t]*(?:from[ \t]+([A-Za-z_][\w.]*)[ \t]+import|import[ \t]+([A-Za-z_][\w.]*))",
    re.MULTILINE,
)
_JS_IMPORT_RE = re.compile(
    r"""(?:from|require\()\s*['"]([^'"]+)['"]""",
)


@dataclass
class Chain:
    """One route from a file nothing imports, down to the dependency."""

    #: Files from the outermost importer to the file that imports the package.
    files: list[Path]
    #: The import line, for the file at the end of the chain.
    lineno: int


def _top_level(name: str) -> str:
    """`rich.console` is `rich`; `@scope/pkg/sub` is `@scope/pkg`."""
    if name.startswith("@"):
        return "/".join(name.split("/")[:2])
    if name.startswith("."):
        # A relative import is local by definition, never a package.
        return ""
    return name.split("/")[0].split(".")[0]


def direct_importers(scan_result, package: str) -> dict[Path, int]:
    """Files that import *package* themselves, and the line where they do.

    Matched on the top-level name, so `from rich.console import Console`
    counts as a use of `rich` -- that is the name in the lockfile, and the
    name someone asking this question types.
    """
    wanted = _top_level(package.strip()).lower()
    found: dict[Path, int] = {}
    if not wanted:
        return found

    for file in getattr(scan_result, "files", []):
        suffix = file.path.suffix.lower()
        if suffix not in (".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
            continue
        try:
            text = file.path.read_text(encoding="utf-8-sig", errors="ignore")
        except Exception:
            continue

        pattern = _PY_IMPORT_RE if suffix == ".py" else _JS_IMPORT_RE
        for match in pattern.finditer(text):
            name = next((g for g in match.groups() if g), "")
            if _top_level(name).lower() != wanted:
                continue
            lineno = text[: match.start()].count("\n") + 1
            # The first import is the one to show: a file importing the same
            # package twice does not have two reasons.
            found.setdefault(file.path, lineno)
            break

    return found


def why(scan_result, analyzer_result, package: str, limit: int = 10) -> list[Chain]:
    """Chains ending at each file that imports *package*.

    Walks the repo's own import graph backwards from the importer, so the
    answer reads outside-in -- `cli.py -> render.py -> rich` says which
    entry point is responsible, which is the actual question.

    Breadth-first and visited-guarded: an import cycle is common and must
    produce a short answer rather than no answer.
    """
    importers = direct_importers(scan_result, package)
    if not importers:
        return []

    graph: dict[Path, set[Path]] = getattr(analyzer_result, "graph", {}) or {}
    reverse: dict[Path, set[Path]] = {}
    for source, targets in graph.items():
        for target in targets:
            reverse.setdefault(target, set()).add(source)

    chains: list[Chain] = []
    for importer, lineno in sorted(importers.items()):
        # Walk outwards to a file nothing imports; that is the entry point a
        # reader recognises. Stop at the first one found per importer.
        path_back: list[Path] = [importer]
        seen = {importer}
        queue: deque[list[Path]] = deque([[importer]])
        while queue:
            route = queue.popleft()
            parents = reverse.get(route[0], set()) - seen
            if not parents:
                path_back = route
                break
            for parent in sorted(parents):
                seen.add(parent)
                queue.append([parent, *route])
        chains.append(Chain(files=path_back, lineno=lineno))
        if len(chains) >= limit:
            break

    # Shortest chain first: the most direct explanation is the useful one.
    chains.sort(key=lambda c: (len(c.files), c.files[-1].name))
    return chains


def render(chains: list[Chain], package: str, root: Path) -> list[str]:
    """The chains as lines, `a.py -> b.py -> package`."""
    if not chains:
        return [f"Nothing imports {package!r}."]

    lines = []
    for chain in chains:
        try:
            names = [f.relative_to(root).as_posix() for f in chain.files]
        except ValueError:
            names = [f.name for f in chain.files]
        lines.append(f"{' -> '.join(names)} -> {package}  (line {chain.lineno})")
    return lines
