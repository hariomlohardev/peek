"""Java edges for the import graph: `import` statements and same-package use.

Regex-based like the JS/TS and Go support, so it needs no JDK. A class is
found by its fully qualified name, built from the file's `package` line and
its file name, so the directory layout (Maven, Gradle, or none) does not
matter:

    import com.acme.model.User;          -> the file declaring com.acme.model.User
    import com.acme.model.User.Role;     -> the same file (nested class)
    import static com.acme.Util.join;    -> the file declaring com.acme.Util
    import com.acme.model.*;             -> the classes of that package this file names

Java imports the file's own package implicitly, so it is treated like a
wildcard import of that package. A wildcard only adds an edge to a class whose
name appears in the file, with comments removed. Reflection, annotation
processors and classes named only inside string literals are not interpreted.
"""

from __future__ import annotations

import re
from pathlib import Path

PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE)
IMPORT_RE = re.compile(r"^\s*import\s+(static\s+)?([\w.]+?)(\.\*)?\s*;", re.MULTILINE)
_COMMENT_RE = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)
_IDENT_RE = re.compile(r"[A-Za-z_$][\w$]*")


def _package_of(text: str) -> str:
    match = PACKAGE_RE.search(text)
    return match.group(1) if match else ""


def _resolve_class(name: str, classes: dict[str, Path]) -> Path | None:
    """The file declaring *name*, or the outer class of a nested class or static member."""
    while name:
        if name in classes:
            return classes[name]
        name = name.rpartition(".")[0]
    return None


def java_targets(
    file: Path,
    text: str,
    classes: dict[str, Path],
    packages: dict[str, list[Path]],
) -> set[Path]:
    """The scanned Java files that *file* imports or names from its own package."""
    code = _COMMENT_RE.sub(" ", text)
    targets: set[Path] = set()
    wildcard_packages = [_package_of(code)]
    for static, name, wildcard in IMPORT_RE.findall(code):
        if wildcard and not static and name in packages:
            wildcard_packages.append(name)
            continue
        target = _resolve_class(name, classes)
        if target is not None:
            targets.add(target)
    words = set(_IDENT_RE.findall(code))
    for package in wildcard_packages:
        for candidate in packages.get(package, ()):
            if candidate.stem in words:
                targets.add(candidate)
    targets.discard(file)
    return targets


def add_java_edges(files, graph: dict[Path, set[Path]]) -> None:
    """Add every scanned `.java` file to *graph* as a node, with its local edges.

    Never raises: an unreadable file stays in the graph as a node without edges.
    """
    java = [f for f in files if f.language == "java" and f.path.suffix.lower() == ".java"]
    if not java:
        return
    texts: dict[Path, str] = {}
    classes: dict[str, Path] = {}
    packages: dict[str, list[Path]] = {}
    for f in java:
        graph.setdefault(f.path, set())
        try:
            text = f.path.read_text(encoding="utf-8-sig", errors="ignore")
        except Exception:
            continue
        texts[f.path] = text
        package = _package_of(_COMMENT_RE.sub(" ", text))
        qualified = f"{package}.{f.path.stem}" if package else f.path.stem
        classes.setdefault(qualified, f.path)
        packages.setdefault(package, []).append(f.path)
    for path, text in texts.items():
        try:
            graph[path].update(java_targets(path, text, classes, packages))
        except Exception:
            continue
