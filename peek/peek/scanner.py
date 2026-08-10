"""Scanner — walks a repo, respects .gitignore, collects stats, detects tech stack & entry points.

Design goals for Day 1:
- < 1 sec for 500-file repos
- Never crash on weird files (binary, syntax error, permission)
- Zero config: works on any path, Python or not
"""

from __future__ import annotations

import ast
import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import pathspec

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FileInfo:
    """Single file discovered by scan()."""

    path: Path          # absolute path
    rel: Path           # relative to scan root
    ext: str            # ".py", ".md", "" etc — lowercased
    size: int           # bytes on disk
    loc: int            # lines of code (non-empty, non-comment heuristic for .py; non-empty for others)
    language: str       # "python", "javascript", "markdown", "yaml", "other"


@dataclass
class ScanResult:
    """Full result of scan(root)."""

    root: Path
    files: list[FileInfo]
    tech_stack: dict[str, str | list[str]]  # e.g. {"primary": "python", "framework": "fastapi", "deps": [...]}
    entry_candidates: list[Path]            # absolute paths, ranked
    stats: dict                             # {"total_files": int, "total_loc": int, "total_bytes": int, "by_lang": {lang: count}}

    @property
    def total_files(self) -> int:
        return self.stats.get("total_files", 0)

    @property
    def total_loc(self) -> int:
        return self.stats.get("total_loc", 0)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_IGNORE_DIRS = {
    "__pycache__", ".git", ".hg", ".svn", ".venv", "venv", "env", ".env",
    "node_modules", "dist", "build", ".tox", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", "eggs", ".eggs", "htmlcov", ".coverage", ".idea", ".vscode",
    "__pycache__", ".next", ".nuxt", "target", "vendor",
}

DEFAULT_IGNORE_FILES = {
    "*.pyc", "*.pyo", "*.so", "*.o", "*.a", "*.egg-info", "*.egg",
}

# Map ext -> language
EXT_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".md": "markdown",
    ".mdx": "markdown",
    ".rst": "rst",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".html": "html",
    ".css": "css",
    ".scss": "css",
    ".sql": "sql",
    ".dockerfile": "docker",
    ".makefile": "make",
}

# Case-insensitive filenames that imply tech stack
TECH_MARKERS: dict[str, tuple[str, str]] = {
    # filename (lower) -> (category, value)
    "pyproject.toml": ("config", "pyproject.toml"),
    "requirements.txt": ("config", "requirements.txt"),
    "requirements-dev.txt": ("config", "requirements-dev.txt"),
    "poetry.lock": ("config", "poetry.lock"),
    "uv.lock": ("config", "uv.lock"),
    "pdm.lock": ("config", "pdm.lock"),
    "package.json": ("config", "package.json"),
    "package-lock.json": ("config", "package-lock.json"),
    "yarn.lock": ("config", "yarn.lock"),
    "pnpm-lock.yaml": ("config", "pnpm-lock.yaml"),
    "cargo.toml": ("config", "cargo.toml"),
    "cargo.lock": ("config", "cargo.lock"),
    "go.mod": ("config", "go.mod"),
    "go.sum": ("config", "go.sum"),
    "gemfile": ("config", "gemfile"),
    "gemfile.lock": ("config", "gemfile.lock"),
    "dockerfile": ("config", "dockerfile"),
    "makefile": ("config", "makefile"),
    "tox.ini": ("config", "tox.ini"),
    "setup.py": ("config", "setup.py"),
    "setup.cfg": ("config", "setup.cfg"),
}

ENTRY_FILENAMES = {
    "main.py", "app.py", "cli.py", "manage.py", "server.py", "api.py",
    "__main__.py", "wsgi.py", "asgi.py", "run.py", "index.py", "core.py",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_binary(path: Path, blocksize: int = 1024) -> bool:
    """Heuristic binary check: null bytes in first block."""
    try:
        with path.open("rb") as f:
            chunk = f.read(blocksize)
            if b"\x00" in chunk:
                return True
            # Also treat very long single-line files as binary-ish (minified)
            if len(chunk) == blocksize and b"\n" not in chunk and len(chunk) > 800:
                return True
    except Exception:
        return True
    return False


def _count_loc(path: Path, language: str) -> int:
    """Count LOC — non-empty lines, stripping Python comments/blank for .py."""
    try:
        if _is_binary(path):
            return 0
        # Guard huge files ( > 1MB ) — approximate
        if path.stat().st_size > 1_000_000:
            # Fast fallback: count newlines without loading all
            try:
                with path.open("rb") as f:
                    return sum(1 for _ in f)
            except Exception:
                return 0
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not text.strip():
            return 0
        lines = text.splitlines()
        if language == "python":
            count = 0
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("#"):
                    continue
                count += 1
            return count
        # Generic: non-empty lines
        return sum(1 for line in lines if line.strip())
    except Exception:
        return 0


def _language_for(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in EXT_TO_LANG:
        return EXT_TO_LANG[ext]
    # Handle extensionless Dockerfiles / Makefiles
    name = path.name.lower()
    if name == "dockerfile" or name.startswith("dockerfile."):
        return "docker"
    if name == "makefile" or name == "gnumakefile":
        return "make"
    return "other"


def _load_ignore_spec(root: Path) -> pathspec.PathSpec:
    """Load .gitignore + .peekignore + defaults into a PathSpec."""
    lines: list[str] = []

    # Defaults
    for d in DEFAULT_IGNORE_DIRS:
        lines.append(f"{d}/")
        lines.append(f"**/{d}/")
    for pat in DEFAULT_IGNORE_FILES:
        lines.append(pat)
        lines.append(f"**/{pat}")

    # .gitignore
    for ignore_file in (".gitignore", ".peekignore"):
        p = root / ignore_file
        if p.is_file():
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
                for line in text.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Negation (!pattern) is supported by pathspec but keep it
                    lines.append(line)
            except Exception:
                pass

    # Also honour .git/info/exclude if present
    exclude = root / ".git" / "info" / "exclude"
    if exclude.is_file():
        try:
            text = exclude.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                lines.append(line)
        except Exception:
            pass

    try:
        return pathspec.PathSpec.from_lines("gitwildmatch", lines)
    except Exception:
        # Fallback: empty spec
        return pathspec.PathSpec.from_lines("gitwildmatch", [])


def _should_ignore(path: Path, root: Path, spec: pathspec.PathSpec) -> bool:
    """Check if relative path should be ignored via spec or default dir names."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    rel_str = rel.as_posix()
    # Quick dir check
    for part in rel.parts:
        if part in DEFAULT_IGNORE_DIRS:
            return True
    # PathSpec check (matches files and dirs)
    if spec.match_file(rel_str):
        return True
    # Also check with trailing slash for dirs
    if path.is_dir() and spec.match_file(rel_str + "/"):
        return True
    return False


# ---------------------------------------------------------------------------
# Tech stack detection
# ---------------------------------------------------------------------------

def detect_tech_stack(root: Path, files: list[FileInfo]) -> dict:
    """Detect tech stack from file presence and pyproject.toml / package.json etc."""
    stack: dict = {"primary": "unknown", "languages": {}, "frameworks": [], "configs": [], "deps": []}
    # Language breakdown
    by_lang: dict[str, int] = {}
    for f in files:
        by_lang[f.language] = by_lang.get(f.language, 0) + 1
    stack["languages"] = by_lang
    # Primary = most common non-markdown/other
    filtered = {k: v for k, v in by_lang.items() if k not in ("markdown", "other")}
    if filtered:
        stack["primary"] = max(filtered, key=lambda k: filtered[k])

    # Config markers present on disk (not just scanned files — check root directly)
    present_configs: list[str] = []
    for marker, (cat, val) in TECH_MARKERS.items():
        # Check exact filename match in scanned files
        low_marker = marker.lower()
        if any(f.rel.name.lower() == low_marker for f in files):
            present_configs.append(val)
        # Also check root-level existence (for files that may be ignored or not scanned due to caps)
        if (root / marker).exists() or (root / marker.capitalize()).exists():
            if val not in present_configs:
                present_configs.append(val)
    # Also detect extensionless Dockerfile/Makefile via direct check
    if (root / "Dockerfile").exists() and "dockerfile" not in present_configs:
        present_configs.append("dockerfile")
    if (root / "Makefile").exists() and "makefile" not in present_configs:
        present_configs.append("makefile")

    stack["configs"] = sorted(set(present_configs))

    # Parse deps from pyproject.toml / package.json / requirements.txt (best-effort, no crash)
    deps: list[str] = []
    # pyproject.toml deps
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            try:
                import tomli as tomllib  # fallback if available
            except ImportError:
                tomllib = None
        if tomllib:
            try:
                data = tomllib.loads(pyproject.read_text(encoding="utf-8", errors="ignore"))
                # PEP 621
                proj = data.get("project", {})
                if "dependencies" in proj:
                    deps.extend([d.split(";")[0].strip() for d in proj["dependencies"]][:15])
                # Poetry
                tool_poetry = data.get("tool", {}).get("poetry", {})
                if "dependencies" in tool_poetry:
                    deps.extend(list(tool_poetry["dependencies"].keys())[:15])
                # PDM / hatch etc. — already covered
                # Detect framework from deps
                dep_str = " ".join(deps).lower()
                if "fastapi" in dep_str:
                    stack["frameworks"].append("FastAPI")
                if "django" in dep_str:
                    stack["frameworks"].append("Django")
                if "flask" in dep_str:
                    stack["frameworks"].append("Flask")
                if "typer" in dep_str:
                    stack["frameworks"].append("Typer")
                if "click" in dep_str:
                    stack["frameworks"].append("Click")
                if "textual" in dep_str:
                    stack["frameworks"].append("Textual")
                if "rich" in dep_str:
                    stack["frameworks"].append("Rich")
                if "sqlalchemy" in dep_str:
                    stack["frameworks"].append("SQLAlchemy")
                if "pydantic" in dep_str:
                    stack["frameworks"].append("Pydantic")
                if "celery" in dep_str:
                    stack["frameworks"].append("Celery")
                if "redis" in dep_str:
                    stack["frameworks"].append("Redis")
                if "pytest" in dep_str:
                    stack["frameworks"].append("pytest")
            except Exception:
                pass

    # package.json
    pkg = root / "package.json"
    if pkg.is_file():
        try:
            import json
            data = json.loads(pkg.read_text(encoding="utf-8", errors="ignore"))
            all_deps = {}
            all_deps.update(data.get("dependencies", {}))
            all_deps.update(data.get("devDependencies", {}))
            deps.extend(list(all_deps.keys())[:15])
            # Framework hints
            if "react" in all_deps:
                stack["frameworks"].append("React")
            if "next" in all_deps:
                stack["frameworks"].append("Next.js")
            if "vue" in all_deps:
                stack["frameworks"].append("Vue")
            if "express" in all_deps:
                stack["frameworks"].append("Express")
        except Exception:
            pass

    # requirements.txt fallback
    if not deps:
        req = root / "requirements.txt"
        if req.is_file():
            try:
                for line in req.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("-"):
                        continue
                    deps.append(line.split("==")[0].split(">=")[0].strip())
                    if len(deps) >= 10:
                        break
            except Exception:
                pass

    stack["deps"] = deps[:15]
    # Deduplicate frameworks
    stack["frameworks"] = sorted(set(stack["frameworks"]))
    return stack


# ---------------------------------------------------------------------------
# Entry point detection
# ---------------------------------------------------------------------------

def _has_main_guard(path: Path) -> bool:
    """Check if file contains if __name__ == '__main__' or def main."""
    try:
        if path.suffix.lower() not in (".py", ".pyi"):
            return False
        if path.stat().st_size > 500_000:
            return False
        text = path.read_text(encoding="utf-8", errors="ignore")
        if 'if __name__' in text and '__main__' in text:
            return True
        # Also check for def main( at top level via ast (more precise)
        if "def main" in text:
            try:
                tree = ast.parse(text)
                for node in tree.body:
                    if isinstance(node, ast.FunctionDef) and node.name == "main":
                        return True
            except Exception:
                pass
    except Exception:
        pass
    return False


def detect_entry_points(root: Path, files: list[FileInfo]) -> list[Path]:
    """Return ranked list of likely entry points (absolute Paths)."""
    scored: list[tuple[float, Path, str]] = []

    # Collect script entry points from pyproject.toml
    script_entries: set[str] = set()
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                tomllib = None
        if tomllib:
            try:
                data = tomllib.loads(pyproject.read_text(encoding="utf-8", errors="ignore"))
                proj_scripts = data.get("project", {}).get("scripts", {})
                script_entries.update(proj_scripts.values())  # e.g. "peek.cli:app"
                poetry_scripts = data.get("tool", {}).get("poetry", {}).get("scripts", {})
                script_entries.update(poetry_scripts.values())
            except Exception:
                pass

    # Dockerfile CMD/ENTRYPOINT check
    docker_entry: str | None = None
    dockerfile = root / "Dockerfile"
    if dockerfile.is_file():
        try:
            txt = dockerfile.read_text(encoding="utf-8", errors="ignore")
            for line in txt.splitlines():
                line = line.strip()
                if line.upper().startswith("CMD") or line.upper().startswith("ENTRYPOINT"):
                    docker_entry = line
                    break
        except Exception:
            pass

    for f in files:
        if f.language != "python" and f.rel.name not in ENTRY_FILENAMES:
            # Only consider python files + known entry filenames (even if not .py, like extensionless)
            continue
        score = 0.0
        reasons: list[str] = []
        name = f.rel.name

        # Filename heuristic — strongest
        if name in ENTRY_FILENAMES:
            score += 10.0
            reasons.append("filename")
        elif name.lower() in ("main.py", "app.py"):
            score += 9.0
            reasons.append("filename")

        # Root-level bonus (entry points usually top-level or app/)
        depth = len(f.rel.parts)
        if depth == 1:
            score += 2.0
        elif depth == 2 and f.rel.parts[0] in ("app", "src", "peek", "project"):
            score += 1.5

        # __main__.py is strong
        if name == "__main__.py":
            score += 8.0

        # Has main guard
        if _has_main_guard(f.path):
            score += 5.0
            reasons.append("main guard")

        # Size penalty — prefer smaller entry files (not 2000-line utils)
        if f.loc > 0:
            if f.loc < 50:
                score += 0.5
            elif f.loc > 500:
                score -= 1.0

        # Script entry bonus (if file matches script entry path)
        for entry in script_entries:
            # entry like "peek.cli:app" -> check if peek/cli.py exists
            if ":" in entry:
                mod_path = entry.split(":")[0].replace(".", "/") + ".py"
                if f.rel.as_posix().endswith(mod_path) or f.rel.as_posix() == mod_path:
                    score += 6.0
                    reasons.append("pyproject.scripts")

        # Dockerfile bonus
        if docker_entry and name.lower() in docker_entry.lower():
            score += 4.0

        if score > 0:
            scored.append((score, f.path, ", ".join(reasons)))

    # Sort descending, take top 5
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p, _ in scored[:5]]


# ---------------------------------------------------------------------------
# Main scan()
# ---------------------------------------------------------------------------

def scan(root: Path | str, max_files: int = 2000) -> ScanResult:
    """Walk `root`, respect ignores, collect FileInfo, detect stack & entries.

    Args:
        root: Path to scan (file or directory). If file, scans its parent.
        max_files: Hard cap to keep < 2 sec on huge repos.

    Returns:
        ScanResult. Never raises — returns empty result on error.
    """
    try:
        root = Path(root).resolve()
        if root.is_file():
            root = root.parent
        if not root.exists() or not root.is_dir():
            return ScanResult(root=root, files=[], tech_stack={}, entry_candidates=[], stats={"total_files": 0, "total_loc": 0, "total_bytes": 0, "by_lang": {}})

        spec = _load_ignore_spec(root)
        files: list[FileInfo] = []
        total_bytes = 0
        total_loc = 0

        # Walk — use rglob but filter dirs early to avoid descending into ignored trees
        # We do manual stack to skip ignored dirs efficiently.
        stack: list[Path] = [root]
        visited: set[Path] = set()

        while stack and len(files) < max_files:
            current = stack.pop()
            try:
                # List entries, sorted for determinism
                entries = sorted(current.iterdir(), key=lambda p: p.name)
            except (PermissionError, OSError):
                continue

            for entry in entries:
                # Skip symlinks that escape root or are broken
                try:
                    if entry.is_symlink():
                        # Resolve and check if inside root
                        try:
                            target = entry.resolve()
                            if not target.is_relative_to(root):
                                continue
                            # Avoid cycles
                            if target in visited:
                                continue
                        except Exception:
                            continue
                except Exception:
                    continue

                if _should_ignore(entry, root, spec):
                    continue

                try:
                    if entry.is_dir():
                        if entry not in visited:
                            visited.add(entry)
                            stack.append(entry)
                    elif entry.is_file():
                        if len(files) >= max_files:
                            break
                        try:
                            stat = entry.stat()
                            size = stat.st_size
                        except Exception:
                            size = 0
                        rel = entry.relative_to(root)
                        ext = entry.suffix.lower()
                        lang = _language_for(entry)
                        loc = _count_loc(entry, lang)
                        info = FileInfo(path=entry.resolve(), rel=rel, ext=ext, size=size, loc=loc, language=lang)
                        files.append(info)
                        total_bytes += size
                        total_loc += loc
                except (PermissionError, OSError):
                    continue

        # Sort files by path for stable output
        files.sort(key=lambda f: f.rel.as_posix())

        tech_stack = detect_tech_stack(root, files)
        entry_candidates = detect_entry_points(root, files)

        by_lang: dict[str, int] = {}
        for f in files:
            by_lang[f.language] = by_lang.get(f.language, 0) + 1

        stats = {
            "total_files": len(files),
            "total_loc": total_loc,
            "total_bytes": total_bytes,
            "by_lang": by_lang,
            "truncated": len(files) >= max_files,
        }

        return ScanResult(root=root, files=files, tech_stack=tech_stack, entry_candidates=entry_candidates, stats=stats)

    except Exception:
        # Never crash — return empty
        try:
            root_p = Path(root).resolve() if isinstance(root, (str, Path)) else Path(".").resolve()
        except Exception:
            root_p = Path(".").resolve()
        return ScanResult(root=root_p, files=[], tech_stack={}, entry_candidates=[], stats={"total_files": 0, "total_loc": 0, "total_bytes": 0, "by_lang": {}})
