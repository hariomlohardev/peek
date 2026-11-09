"""Why is this package here? — trace an external dependency back to the code.

`peek graph` answers "what imports what" between the repo's own files.
This answers the question you ask when a dependency shows up in a lockfile
and nobody remembers asking for it: which file imports it, and what leads
there from the outside.
"""

from __future__ import annotations

import ast
import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path

_JS_IMPORT_RE = re.compile(
    r"""(?<![\w$])(?:from|require\s*\(|import)\s*(['"])([^'"\r\n]+)\1""",
)


def _js_without_comments(text: str) -> tuple[str, str]:
    """Mask JS comments without changing offsets or line breaks.

    The second string masks quoted literals too, so an import-like phrase
    inside a string is not counted. This is a static scan, not a JS parser:
    regex literals and template interpolation are not interpreted.
    """
    visible = list(text)
    code = list(text)
    quote = None
    escaped = False
    i = 0
    while i < len(text):
        char = text[i]
        next_char = text[i + 1] if i + 1 < len(text) else ""
        if quote is not None:
            code[i] = "\n" if char == "\n" else " "
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            i += 1
            continue
        if char in ("'", '"', "`"):
            quote = char
            code[i] = " "
            i += 1
            continue
        if char == "/" and next_char in ("/", "*"):
            line_comment = next_char == "/"
            end = text.find("\n", i + 2) if line_comment else text.find("*/", i + 2)
            if end == -1:
                end = len(text)
            elif not line_comment:
                end += 2
            for index in range(i, end):
                if text[index] != "\n":
                    visible[index] = code[index] = " "
            i = end
            continue
        i += 1
    return "".join(visible), "".join(code)


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
    name someone asking this question types. Unreadable or unparseable
    Python files are skipped: they provide no reliable import evidence.
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

        if suffix == ".py":
            try:
                tree = ast.parse(text)
            except (SyntaxError, ValueError, RecursionError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module]
                else:
                    continue
                if any(_top_level(name).lower() == wanted for name in names):
                    # ast.walk is breadth-first, so a nested import may occur
                    # earlier in the source than one visited before it.
                    found[file.path] = min(found.get(file.path, node.lineno), node.lineno)
            continue

        visible, code = _js_without_comments(text)
        for match in _JS_IMPORT_RE.finditer(visible):
            if code[match.start()].isspace():
                continue
            name = match.group(2)
            if _top_level(name).lower() != wanted:
                continue
            lineno = visible.count("\n", 0, match.start()) + 1
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
