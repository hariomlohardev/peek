"""Analyzer — builds import graph, ranks files, generates heuristic summary.

Day 2 scope:
- AST import extraction (Import / ImportFrom, relative resolution)
- Graph: dict[Path, set[Path]] file -> {local deps}
- PageRank-lite (5 iterations) + in-degree + entry bonus -> RankedFile
- Heuristic summarize() -> one-liner English summary

v3 Day 1 — Polyglot: also handles javascript/typescript via regex import extraction.

Never crashes: skips SyntaxError, handles huge files, namespace packages, circular imports.
"""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from peek.scanner import ScanResult, FileInfo

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RankedFile:
    """A file with centrality score."""

    path: Path          # absolute
    rel: Path           # relative to root
    score: float
    reasons: list[str]

    # For JSON/Rich convenience
    @property
    def name(self) -> str:
        return self.rel.as_posix()


@dataclass
class AnalyzerResult:
    """Full result of analyze(scan_result)."""

    root: Path
    graph: dict[Path, set[Path]]
    reverse_graph: dict[Path, set[Path]]
    ranked: list[RankedFile]
    summary: str
    tech_stack: dict
    external_imports: set[str]
    stats: dict  # passthrough from ScanResult + graph stats


# ---------------------------------------------------------------------------
# Polyglot regexes (JS/TS) — no hard dep, fallback to regex
# ---------------------------------------------------------------------------

JS_IMPORT_RE = re.compile(r"""import\s+(?:.*?\s+from\s+)?['"]([^'"]+)['"]|require\(['"]([^'"]+)['"]\)""")
JS_EXPORT_RE = re.compile(r"""export\s+(?:default\s+)?(?:function|class|const|let|var)\s+(\w+)""")

# ---------------------------------------------------------------------------
# Module index building
# ---------------------------------------------------------------------------

_SRC_PREFIXES = ("src", "app", "lib", "source", "project")


def _module_name_for(rel: Path, is_init: bool) -> str:
    """Derive logical module name for a file relative to scan root."""
    if is_init:
        if len(rel.parts) == 1:
            return ""
        return ".".join(rel.parts[:-1])
    # normal file
    mod = ".".join(rel.with_suffix("").parts)
    # If under src/app etc., strip prefix so `src/peek/x.py` -> peek.x
    if len(rel.parts) > 1 and rel.parts[0] in _SRC_PREFIXES:
        stripped = ".".join(rel.with_suffix("").parts[1:])
        # Prefer stripped as logical name
        return stripped
    return mod


def _build_module_index(files: list[FileInfo], root: Path) -> dict[str, Path]:
    """Map logical module name -> absolute path."""
    index: dict[str, Path] = {}
    for f in files:
        if f.language != "python":
            continue
        if f.path.suffix.lower() not in (".py", ".pyi"):
            continue
        rel = f.rel
        is_init = rel.name == "__init__.py"
        mod = _module_name_for(rel, is_init)
        if not mod:
            continue
        # Primary name
        if mod not in index:
            index[mod] = f.path
        # Also register the dotted path with suffix stripped verbatim for exact file lookup
        # e.g. "peek.scanner" and "src.peek.scanner" both -> same file via suffix fallback
        # But we already have logical; also keep raw with_prefix as alias
        raw_mod = ".".join(rel.with_suffix("").parts)
        if raw_mod != mod and raw_mod not in index:
            index[raw_mod] = f.path
        # For __init__, also register long form `peek.__init__` -> file
        if is_init:
            long_mod = ".".join(rel.with_suffix("").parts)  # peek.__init__
            if long_mod not in index:
                index[long_mod] = f.path
    return index


def _relative_base(package: str, level: int) -> str | None:
    """Compute base package for a relative import level.

    Args:
        package: current package (e.g. "peek.sub" or "peek" or "")
        level: ImportFrom.level (1 = same package, 2 = parent, ...)

    Returns absolute base string, "" for top-level, or None if invalid/beyond top.
    """
    if level == 0:
        return None
    if not package:
        # top-level file has no package; any relative import is invalid
        return None
    parts = package.split(".")
    if level == 1:
        return package
    # level >=2
    if level - 1 > len(parts):
        return None
    keep = len(parts) - level + 1
    if keep <= 0:
        return ""
    return ".".join(parts[:keep])


def _extract_raw_imports(path: Path, module_name: str, is_init: bool) -> tuple[set[str], set[str]]:
    """Parse file and return (raw_local_candidates, external_candidates).

    We return all dotted import strings seen; caller resolves which are local.
    External vs local not distinguished here — both in one set; caller partitions.
    We return single set; external detection happens after resolution.
    """
    raw: set[str] = set()
    try:
        if path.stat().st_size > 500_000:
            # Large file — still try but cap read
            pass
        # Use utf-8-sig to handle BOM (PowerShell creates BOM files)
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except Exception:
            text = path.read_text(encoding="utf-8", errors="ignore")
        if not text.strip():
            return raw, set()
        # Strip leading BOM if still present
        if text.startswith("﻿"):
            text = text.lstrip("﻿")
        tree = ast.parse(text, filename=str(path))
    except (SyntaxError, UnicodeDecodeError, ValueError, OSError, RecursionError):
        return raw, set()

    package = module_name if is_init else (module_name.rpartition(".")[0] if "." in module_name else "")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # alias.name is like "os" or "peek.scanner"
                raw.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            level = node.level
            mod = node.module  # may be None
            if level == 0:
                if mod:
                    raw.add(mod)
                    for alias in node.names:
                        if alias.name == "*":
                            continue
                        # candidate for submodule import: from peek.scanner import Foo -> peek.scanner.Foo
                        raw.add(f"{mod}.{alias.name}")
            else:
                base = _relative_base(package, level)
                if base is None:
                    continue
                if mod:
                    abs_mod = f"{base}.{mod}" if base else mod
                    raw.add(abs_mod)
                    for alias in node.names:
                        if alias.name == "*":
                            continue
                        raw.add(f"{abs_mod}.{alias.name}")
                else:
                    # from . import foo, bar
                    for alias in node.names:
                        if alias.name == "*":
                            continue
                        abs_name = f"{base}.{alias.name}" if base else alias.name
                        raw.add(abs_name)
                        # Also consider base itself? from . import foo may also imply base is used
                        # Add base once
                        if base:
                            raw.add(base)
    return raw, set()


def _resolve_local_import(import_name: str, index: dict[str, Path]) -> Path | None:
    """Resolve dotted import name to local file if possible (longest prefix match).

    Handles src-layout suffix fallback: `peek.scanner` matches index `src.peek.scanner`.
    """
    # Exact match
    if import_name in index:
        return index[import_name]
    parts = import_name.split(".")
    # Longest parent prefix exact or suffix fallback
    # First try parent exact matches
    for i in range(len(parts) - 1, 0, -1):
        cand = ".".join(parts[:i])
        if cand in index:
            return index[cand]
        # suffix fallback for cand: any indexed mod ending with .cand
        for mod, p in index.items():
            if mod == cand or mod.endswith("." + cand):
                return p
    # Finally try full name suffix fallback (src layout)
    for mod, p in index.items():
        if mod == import_name or mod.endswith("." + import_name):
            return p
    return None


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph(files: list[FileInfo], root: Path) -> tuple[dict[Path, set[Path]], set[str], dict[str, Path]]:
    """Build import graph.

    Polyglot: handles python + javascript + typescript.
    Returns (graph, external_imports, module_index)
    - graph: dict absolute Path -> set[absolute Path] (python + js/ts nodes)
    - external_imports: set of import names not resolved locally (python only)
    """
    index = _build_module_index(files, root)

    # Path -> FileInfo for JS/TS resolution (absolute resolved paths)
    path_to_file: dict[Path, FileInfo] = {f.path.resolve(): f for f in files}

    # Init graph nodes for python + js/ts files
    graph: dict[Path, set[Path]] = {}
    for f in files:
        if f.language == "python" and f.path.suffix.lower() in (".py", ".pyi"):
            graph[f.path] = set()
        elif f.language in ("javascript", "typescript"):
            graph[f.path] = set()

    external: set[str] = set()

    for f in files:
        # --- Python ---
        if f.language == "python" and f.path.suffix.lower() in (".py", ".pyi"):
            rel = f.rel
            is_init = rel.name == "__init__.py"
            mod = _module_name_for(rel, is_init)
            raw_imports, _ = _extract_raw_imports(f.path, mod, is_init)
            node = f.path
            if node not in graph:
                graph[node] = set()
            for imp in raw_imports:
                target = _resolve_local_import(imp, index)
                if target is not None:
                    if target == node:
                        continue
                    if target in graph:
                        graph[node].add(target)
                    else:
                        graph.setdefault(target, set())
                        graph[node].add(target)
                else:
                    top = imp.split(".")[0]
                    if top and not top.startswith("_"):
                        is_stdlib = False
                        try:
                            if hasattr(sys, "stdlib_module_names"):
                                is_stdlib = top in sys.stdlib_module_names
                            else:
                                _stdlib_fallback = {"os","sys","ast","pathlib","dataclasses","typing","collections","json","re","io","time","datetime","functools","itertools","math","random","hashlib","subprocess","shutil","glob","fnmatch","importlib","inspect","textwrap","string","enum","abc","copy","pickle","struct","socket","threading","asyncio","unittest","http","urllib","email","html","xml","csv","logging","argparse","difflib","tempfile","traceback","warnings","weakref","types","queue","contextlib","select","selectors","signal","stat","uuid","zlib","gzip","zipfile","tarfile","platform","getpass","pwd","grp","site","codecs","unicodedata","operator","heapq","bisect","array","decimal","fractions","numbers","itertools"}
                                is_stdlib = top in _stdlib_fallback
                        except Exception:
                            is_stdlib = False
                        if not is_stdlib:
                            external.add(top)
        # --- JS / TS ---
        elif f.language in ("javascript", "typescript"):
            try:
                try:
                    text = f.path.read_text(encoding="utf-8-sig", errors="ignore")
                except Exception:
                    text = f.path.read_text(encoding="utf-8", errors="ignore")
                if not text.strip():
                    continue
                if text.startswith("﻿"):
                    text = text.lstrip("﻿")
                for m in JS_IMPORT_RE.finditer(text):
                    imp = m.group(1) or m.group(2)
                    if not imp:
                        continue
                    if imp.startswith("."):
                        # Relative import — resolve to local file
                        try:
                            target = (f.path.parent / imp).resolve()
                        except Exception:
                            continue
                        # Try candidate extensions as per brief
                        for ext in ["", ".js", ".ts", ".jsx", ".tsx", "/index.js", "/index.ts"]:
                            try:
                                cand = Path(str(target) + ext)
                                # cand may already be resolved; normalize via resolve where possible
                                # path_to_file keys are resolved, so check resolved cand if exists
                                # If cand exists on disk and is in scanned files, add edge
                                if cand in path_to_file:
                                    graph[f.path].add(cand)
                                    break
                                # Also try resolved cand
                                try:
                                    rcand = cand.resolve()
                                    if rcand in path_to_file:
                                        graph[f.path].add(rcand)
                                        break
                                except Exception:
                                    pass
                                # Also handle case where target already had extension and ext=="" gave us the file
                                # Try with exact target if it is a file
                                if ext == "" and target in path_to_file:
                                    graph[f.path].add(target)
                                    break
                                try:
                                    if ext == "" and target.resolve() in path_to_file:
                                        graph[f.path].add(target.resolve())
                                        break
                                except Exception:
                                    pass
                            except Exception:
                                continue
                    # non-relative (e.g., 'react') is external — ignored for graph edges
            except Exception:
                continue
    return graph, external, index


def build_reverse_graph(graph: dict[Path, set[Path]]) -> dict[Path, set[Path]]:
    rev: dict[Path, set[Path]] = {n: set() for n in graph}
    for src, deps in graph.items():
        for dst in deps:
            rev.setdefault(dst, set()).add(src)
            rev.setdefault(src, set())
    return rev


# ---------------------------------------------------------------------------
# Ranking (PageRank-lite + in-degree + entry bonus)
# ---------------------------------------------------------------------------

def _pagerank(graph: dict[Path, set[Path]], iterations: int = 5, damping: float = 0.85) -> dict[Path, float]:
    nodes = list(graph.keys())
    N = len(nodes)
    if N == 0:
        return {}
    # init uniform
    rank: dict[Path, float] = {n: 1.0 / N for n in nodes}
    out_deg: dict[Path, int] = {n: len(graph[n]) for n in nodes}

    for _ in range(iterations):
        new_rank: dict[Path, float] = {}
        # dangling mass (nodes with no out edges)
        dangling_sum = sum(rank[n] for n in nodes if out_deg[n] == 0)
        # Build reverse for quick sum
        rev = build_reverse_graph(graph)
        for node in nodes:
            s = 0.0
            for prev in rev.get(node, set()):
                od = out_deg[prev]
                if od > 0:
                    s += rank[prev] / od
                # dangling prev already handled via dangling_sum, skip
            # add dangling distributed evenly
            s += dangling_sum / N
            new_rank[node] = (1.0 - damping) / N + damping * s
        rank = new_rank
    return rank


def _has_main_guard(path: Path) -> bool:
    """Local copy of scanner's _has_main_guard — AST based, no substring false positives."""
    try:
        if path.suffix.lower() not in (".py", ".pyi"):
            return False
        if path.stat().st_size > 500_000:
            return False
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except Exception:
            text = path.read_text(encoding="utf-8", errors="ignore")
        if text.startswith("﻿"):
            text = text.lstrip("﻿")
        if not text.strip():
            return False
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                try:
                    test = node.test
                    if isinstance(test, ast.Compare):
                        left = test.left
                        if isinstance(left, ast.Name) and left.id == "__name__":
                            for comp in test.comparators:
                                if isinstance(comp, ast.Constant) and comp.value == "__main__":
                                    return True
                except Exception:
                    continue
            if isinstance(node, ast.FunctionDef) and node.name == "main":
                return True
    except (SyntaxError, UnicodeDecodeError, ValueError, OSError, RecursionError):
        return False
    except Exception:
        pass
    return False


def rank_files(
    graph: dict[Path, set[Path]],
    entry_candidates: list[Path],
    root: Path,
) -> list[RankedFile]:
    nodes = list(graph.keys())
    if not nodes:
        # No python graph — rank entry candidates by themselves
        ranked: list[RankedFile] = []
        for p in entry_candidates[:5]:
            try:
                rel = p.relative_to(root)
            except ValueError:
                rel = p.name if isinstance(p, Path) else Path(str(p))
                rel = Path(rel)
            ranked.append(RankedFile(path=p, rel=rel, score=10.0 - len(ranked), reasons=["entry point"]))
        return ranked

    rev = build_reverse_graph(graph)
    pr = _pagerank(graph, iterations=5)
    max_pr = max(pr.values()) if pr else 1.0
    out_deg = {n: len(graph[n]) for n in nodes}
    entry_set = set(entry_candidates)

    scored: list[RankedFile] = []
    for node in nodes:
        try:
            rel = node.relative_to(root)
        except ValueError:
            rel = Path(node.name)
        # pr normalized 0..5
        pr_norm = (pr.get(node, 0) / max_pr * 5.0) if max_pr else 0
        in_deg = len(rev.get(node, set()))
        in_norm = min(in_deg * 1.2, 5.0)
        entry_bonus = 5.0 if node in entry_set else 0.0
        guard_bonus = 0.5 if _has_main_guard(node) else 0.0

        score = pr_norm + in_norm + entry_bonus + guard_bonus
        # Small depth bonus: prefer shallower files slightly (entries vs deep utils)
        try:
            depth = len(rel.parts)
            if depth == 1:
                score += 0.3
            elif depth == 2:
                score += 0.15
        except Exception:
            pass

        # Penalize __init__.py (package init) — not a starting point
        if rel.name == "__init__.py":
            score -= 3.0

        # Penalize tiny files (<10 LOC) — likely __init__ or stub
        try:
            # quick LOC from file size as proxy to avoid re-reading scanner stats
            # Use line count heuristic
            try:
                text = node.read_text(encoding="utf-8-sig", errors="ignore")
            except Exception:
                text = node.read_text(encoding="utf-8", errors="ignore")
            if text.startswith("﻿"):
                text = text.lstrip("﻿")
            loc_est = sum(1 for l in text.splitlines() if l.strip() and not l.strip().startswith("#"))
            if loc_est < 10:
                score -= 1.5
            elif loc_est < 30:
                score -= 0.5
        except Exception:
            pass

        reasons: list[str] = []
        if node in entry_set:
            reasons.append("entry point")
        if _has_main_guard(node):
            reasons.append("main guard")
        if in_deg >= 3:
            reasons.append(f"hub (imported by {in_deg})")
        elif in_deg >= 1:
            reasons.append(f"imported by {in_deg}")
        if pr_norm > 3.0:
            reasons.append("central")
        if out_deg.get(node, 0) >= 4:
            reasons.append(f"connects {out_deg[node]} modules")
        if not reasons:
            reasons.append("module")

        scored.append(RankedFile(path=node, rel=rel, score=score, reasons=reasons))

    scored.sort(key=lambda r: r.score, reverse=True)
    return scored


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

_FRAMEWORK_IMPORT_MAP: dict[str, str] = {
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "typer": "Typer",
    "click": "Click",
    "textual": "Textual",
    "rich": "Rich",
    "sqlalchemy": "SQLAlchemy",
    "pydantic": "Pydantic",
    "celery": "Celery",
    "redis": "Redis",
    "pytest": "pytest",
    "numpy": "NumPy",
    "pandas": "pandas",
    "torch": "PyTorch",
    "transformers": "Transformers",
    "starlette": "Starlette",
    "uvicorn": "Uvicorn",
    "httpx": "HTTPX",
    "requests": "requests",
    "aiohttp": "aiohttp",
    "sqlmodel": "SQLModel",
    "alembic": "Alembic",
    "psycopg2": "Postgres",
    "psycopg": "Postgres",
    "asyncpg": "Postgres",
    "pymongo": "MongoDB",
    "motor": "MongoDB",
    "boto3": "AWS",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "langchain": "LangChain",
}

_DB_KEYWORDS = {"sqlalchemy", "psycopg2", "psycopg", "asyncpg", "pymongo", "motor", "sqlite", "alembic", "sqlmodel"}


def summarize(
    graph: dict[Path, set[Path]],
    ranked: list[RankedFile],
    tech_stack: dict,
    external_imports: set[str],
    scan_stats: dict,
) -> str:
    # Gather frameworks from tech_stack + external_imports
    frameworks: list[str] = list(tech_stack.get("frameworks", []))
    lower_external = {e.lower() for e in external_imports}
    for imp_lower, label in _FRAMEWORK_IMPORT_MAP.items():
        if imp_lower in lower_external and label not in frameworks:
            frameworks.append(label)
    frameworks = sorted(set(frameworks))

    primary = tech_stack.get("primary", "unknown")
    total_py = len(graph)
    total_files = scan_stats.get("total_files", 0)
    total_loc = scan_stats.get("total_loc", 0)

    # Determine project type
    fw_set = set(frameworks)
    type_hint = ""
    if "FastAPI" in fw_set:
        if fw_set & {"SQLAlchemy", "Postgres", "SQLModel", "Alembic"}:
            type_hint = "FastAPI + SQLAlchemy API"
        else:
            type_hint = "FastAPI API"
    elif "Django" in fw_set:
        type_hint = "Django web app"
    elif "Flask" in fw_set:
        type_hint = "Flask app"
    elif "Typer" in fw_set or "Click" in fw_set:
        type_hint = "Typer/Click CLI tool"
    elif "Textual" in fw_set:
        type_hint = "Textual TUI app"
    elif "Rich" in fw_set:
        type_hint = "Rich CLI"
    elif primary == "python" and total_py:
        type_hint = "Python project"
    elif primary != "unknown":
        type_hint = f"{primary} project"
    else:
        type_hint = "project"

    # Entry / hub info
    entry_str = ""
    if ranked:
        # Prefer actual entry point, not just top scored hub
        entry_candidate = next((r for r in ranked if "entry point" in r.reasons), ranked[0])
        entry_str = entry_candidate.rel.as_posix()
    hub_str = ""
    if ranked:
        # hub is most imported
        hub = max(ranked, key=lambda r: next((int(p.split()[-1].rstrip(")")) for p in r.reasons if "hub" in p), -1), default=ranked[0])
        # Alternative: pick ranked with max in-degree reason
        hub_in = 0
        hub_candidate = ranked[0]
        for r in ranked:
            for rs in r.reasons:
                if rs.startswith("hub"):
                    try:
                        n = int(rs.split("imported by")[1].strip().rstrip(")"))
                        if n > hub_in:
                            hub_in = n
                            hub_candidate = r
                    except Exception:
                        pass
        if hub_in >= 2:
            hub_str = f"core hub is `{hub_candidate.rel.as_posix()}` (imported by {hub_in})"
    db_hint = ""
    if lower_external & _DB_KEYWORDS:
        if "psycopg2" in lower_external or "psycopg" in lower_external or "asyncpg" in lower_external:
            db_hint = "with Postgres"
        elif "pymongo" in lower_external or "motor" in lower_external:
            db_hint = "with MongoDB"
        elif "sqlalchemy" in lower_external:
            db_hint = "with SQLAlchemy"

    # Build sentence
    if total_py == 0:
        return f"{type_hint} — {total_files} files, {total_loc} LOC, no Python modules detected."

    parts: list[str] = []
    # First sentence: type + frameworks + stats
    if frameworks:
        fw_preview = ", ".join(frameworks[:4])
        parts.append(f"{type_hint} ({fw_preview}) — {total_py} Python modules, {total_loc} LOC.")
    else:
        parts.append(f"{type_hint} — {total_py} Python modules, {total_loc} LOC.")

    # Second: structure
    if ranked:
        edge_count = sum(len(v) for v in graph.values())
        sec = f"Entry: `{entry_str}`"
        if hub_str:
            sec += f" • {hub_str}"
        sec += f" • {edge_count} import edges."
        parts.append(sec)

    if db_hint and "with Postgres" not in " ".join(parts) and "with MongoDB" not in " ".join(parts):
        parts[-1] += f" {db_hint}."

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Public API: analyze()
# ---------------------------------------------------------------------------

def analyze(scan_result: ScanResult) -> AnalyzerResult:
    """Run full analysis: graph -> ranking -> summary."""
    root = scan_result.root
    graph, external, _ = build_graph(scan_result.files, root)
    rev = build_reverse_graph(graph)
    ranked = rank_files(graph, scan_result.entry_candidates, root)
    summary = summarize(graph, ranked, scan_result.tech_stack, external, scan_result.stats)

    stats = dict(scan_result.stats)
    stats.update({"graph_nodes": len(graph), "graph_edges": sum(len(v) for v in graph.values())})

    return AnalyzerResult(
        root=root,
        graph=graph,
        reverse_graph=rev,
        ranked=ranked,
        summary=summary,
        tech_stack=scan_result.tech_stack,
        external_imports=external,
        stats=stats,
    )
