"""Rust edges for the import graph: `mod` declarations and `use` paths.

Regex-based like the JS/TS and Go support, so it needs no Rust toolchain. It
follows what the module system maps onto files:

    mod config;                 -> config.rs or config/mod.rs
    use crate::net::tcp::Conn;  -> net/tcp.rs (the deepest module that is a file)
    use super::util;            -> ../util.rs
    use my_core::Thing;         -> src/lib.rs of the workspace crate `my-core`

Items that live inside a file (a struct, a function) resolve to the file of the
module that owns them. Macros, `include!` and conditional compilation are not
interpreted.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_VIS = r"(?:pub(?:\([^)]*\))?\s+)?"
# Only `mod foo;` -- an inline `mod foo { ... }` has no file of its own.
MOD_RE = re.compile(
    r'^[ \t]*(?:#\[path\s*=\s*"([^"]+)"\]\s*)?' + _VIS + r"mod\s+([A-Za-z_]\w*)\s*;",
    re.MULTILINE,
)
USE_RE = re.compile(r"^[ \t]*" + _VIS + r"use\s+([^;]+);", re.MULTILINE)
INLINE_MOD_RE = re.compile(r"^[ \t]*" + _VIS + r"mod\s+[A-Za-z_]\w*\s*\{", re.MULTILINE)

# Files whose child modules sit next to them rather than in a directory named
# after them.
_DIR_OWNERS = ("mod.rs", "lib.rs", "main.rs")


def _expand_use(tree: str) -> list[str]:
    """Flatten `a::{b, c::{d, e}}` into `a::b`, `a::c::d` and `a::c::e`."""
    tree = tree.strip()
    brace = tree.find("{")
    if brace == -1:
        return [tree] if tree else []
    prefix = tree[:brace]
    parts: list[str] = []
    depth = 0
    start = brace + 1
    for i in range(brace, len(tree)):
        ch = tree[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                parts.append(tree[start:i])
                break
        elif ch == "," and depth == 1:
            parts.append(tree[start:i])
            start = i + 1
    out: list[str] = []
    for part in parts:
        if part.strip():
            out.extend(_expand_use(prefix + part.strip()))
    return out


def _inline_spans(text: str) -> list[tuple[int, int]]:
    """Start and end offsets of the body of every inline `mod name { ... }`.

    Braces are counted without parsing strings or comments, which is enough to
    tell that the `use super::*;` of a `mod tests { ... }` block is one module
    deeper than the file it sits in.
    """
    spans: list[tuple[int, int]] = []
    for match in INLINE_MOD_RE.finditer(text):
        depth = 0
        end = len(text)
        for i in range(match.end() - 1, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        spans.append((match.end(), end))
    return spans


def _segments(path: str) -> list[str]:
    """`crate::a::B as C` -> ["crate", "a", "B"]; a glob or trailing `self` is dropped."""
    path = re.split(r"\s+as\s+", path.strip())[0]
    if path.startswith("::"):
        return []  # `::name` always means an external crate
    segs = [s.strip().removeprefix("r#") for s in path.split("::")]
    while segs and segs[-1] in ("*", "self", ""):
        segs.pop()
    return segs if all(re.fullmatch(r"\w+", s) for s in segs) else []


def _child_dir(file: Path) -> Path:
    """The directory that holds the child modules of *file*."""
    return file.parent if file.name in _DIR_OWNERS else file.parent / file.stem


def _known(cand: Path, rust_files: dict[str, Path]) -> Path | None:
    """The scanned file spelled exactly like *cand*.

    Looked up by spelling rather than as a Path: Windows paths compare
    case-insensitively, which would make the item `crate::Config` match the
    module file `config.rs`. Rust module names are case-sensitive.
    """
    return rust_files.get(str(cand))


def _module_file(module_dir: Path, rust_files: dict[str, Path]) -> Path | None:
    """The file of the module whose children live in *module_dir*."""
    for cand in (
        module_dir.with_name(module_dir.name + ".rs"),
        module_dir / "mod.rs",
        module_dir / "lib.rs",
        module_dir / "main.rs",
    ):
        known = _known(cand, rust_files)
        if known is not None:
            return known
    return None


def _descend(base: Path, segs: list[str], rust_files: dict[str, Path]) -> Path | None:
    """Follow *segs* below *base* and return the deepest module that is a file."""
    found = None
    current = base
    for seg in segs:
        current = current / seg
        for cand in (current.with_name(seg + ".rs"), current / "mod.rs"):
            known = _known(cand, rust_files)
            if known is not None:
                found = known
                break
        else:
            break
    return found


def _crate_dir(file: Path, root: Path, rust_files: dict[str, Path]) -> Path | None:
    """The directory of the crate root (`lib.rs` or `main.rs`) that *file* belongs to."""
    current = file.parent
    while True:
        if _known(current / "lib.rs", rust_files) or _known(current / "main.rs", rust_files):
            return current
        if current == root or current.parent == current:
            return None
        current = current.parent


def _workspace_crates(rust_files: dict[str, Path]) -> dict[str, Path]:
    """Crate name as written in `use` (dashes become underscores) -> directory of its lib.rs."""
    crates: dict[str, Path] = {}
    try:
        import tomllib
    except ImportError:  # pragma: no cover - Python 3.11+ always has it
        return crates
    for lib in sorted(p for p in rust_files.values() if p.name == "lib.rs"):
        package_dir = lib.parent.parent if lib.parent.name == "src" else lib.parent
        try:
            data = tomllib.loads(
                (package_dir / "Cargo.toml").read_text(encoding="utf-8", errors="ignore")
            )
            name = data["package"]["name"]
        except Exception:
            continue
        if isinstance(name, str) and name:
            crates.setdefault(name.replace("-", "_"), lib.parent)
    return crates


def _resolve_use(
    file: Path,
    segs: list[str],
    inline_depth: int,
    root: Path,
    rust_files: dict[str, Path],
    crates: dict[str, Path],
) -> Path | None:
    """The file a `use` path leads to, written *inline_depth* inline modules deep in *file*."""
    head = segs[0]
    if head == "crate":
        base = _crate_dir(file, root, rust_files)
        if base is None:
            return None
        return _descend(base, segs[1:], rust_files) or _module_file(base, rust_files)
    if head in crates:
        base = crates[head]
        return _descend(base, segs[1:], rust_files) or _module_file(base, rust_files)
    # Each leading `super` first climbs out of an inline module. Only once the
    # path is back at the file's own module can it name another file.
    while inline_depth and segs and segs[0] == "super":
        segs = segs[1:]
        inline_depth -= 1
    if inline_depth or not segs:
        return None
    if segs[0] == "super":
        base = _child_dir(file)
        while segs and segs[0] == "super":
            base = base.parent
            segs = segs[1:]
        return _descend(base, segs, rust_files) or _module_file(base, rust_files)
    if segs[0] == "self":
        segs = segs[1:]
    # `use config::Settings;` -- a child module of this one. An external crate
    # or `std` finds no file here and adds no edge.
    return _descend(_child_dir(file), segs, rust_files)


def _resolve_mod(
    file: Path, name: str, attr_path: str | None, rust_files: dict[str, Path]
) -> Path | None:
    if attr_path:
        cand = Path(os.path.normpath(file.parent / attr_path))
        return _known(cand, rust_files)
    # A crate root that is not lib.rs/main.rs (tests/it.rs, src/bin/tool.rs)
    # keeps its modules beside it, so the sibling directory is tried as well.
    for base in dict.fromkeys((_child_dir(file), file.parent)):
        for cand in (base / f"{name}.rs", base / name / "mod.rs"):
            known = _known(cand, rust_files)
            if known is not None:
                return known
    return None


def rust_targets(
    file: Path, text: str, root: Path, rust_files: dict[str, Path], crates: dict[str, Path]
) -> set[Path]:
    """The scanned Rust files that *file* declares as modules or imports from."""
    targets: set[Path] = set()
    spans = _inline_spans(text)

    def inline_depth(offset: int) -> int:
        return sum(1 for start, end in spans if start <= offset < end)

    for match in MOD_RE.finditer(text):
        # A `mod x;` nested in an inline module lives in a directory named
        # after that module; rare enough to leave unresolved.
        if inline_depth(match.start()):
            continue
        target = _resolve_mod(file, match.group(2), match.group(1), rust_files)
        if target is not None:
            targets.add(target)
    for match in USE_RE.finditer(text):
        depth = inline_depth(match.start())
        for path in _expand_use(match.group(1)):
            segs = _segments(path)
            if not segs:
                continue
            target = _resolve_use(file, segs, depth, root, rust_files, crates)
            if target is not None:
                targets.add(target)
    targets.discard(file)
    return targets


def add_rust_edges(files, root: Path, graph: dict[Path, set[Path]]) -> None:
    """Add every scanned `.rs` file to *graph* as a node, with its local edges.

    Never raises: an unreadable file stays in the graph as a node without edges.
    """
    rust = [f for f in files if f.language == "rust" and f.path.suffix.lower() == ".rs"]
    if not rust:
        return
    rust_files = {str(f.path): f.path for f in rust}
    for path in rust_files.values():
        graph.setdefault(path, set())
    try:
        crates = _workspace_crates(rust_files)
    except Exception:
        crates = {}
    for f in rust:
        try:
            text = f.path.read_text(encoding="utf-8-sig", errors="ignore")
            graph[f.path].update(rust_targets(f.path, text, root, rust_files, crates))
        except Exception:
            continue
