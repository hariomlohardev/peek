# Five-Day Build Plan — `peek` v0.1.0

> **Assumption:** All-day coding, ~10–12 hours/day, one person (or two pairing). Python-primary. Goal: shippable `peek` v0.1.0 on PyPI + GitHub by end of Day 5, with demo GIF and launch-ready README.
>
> **Total estimated effort:** ~45 hours of focused work + 5 hours buffer.

---

## Overview

| Day | Theme | Deliverable by EOD | Hours |
|---|---|---|---|
| **1** | Scanner + Project Scaffolding | `peek scan .` prints file stats + tech stack | 9 |
| **2** | Analyzer (AST graph + ranking + summary) | `peek analyze .` prints ranked "start here" + summary | 10 |
| **3** | Renderer — Static (Rich) + TUI (Textual) | `peek .` shows beautiful output, TUI navigable | 10 |
| **4** | Polish, P1 features, Testing | `--html`, `--pack`, `--find`, tests, edge cases | 9 |
| **5** | Packaging, Demo, Docs, Launch | PyPI + GitHub + GIF + README + launch posts | 8 |

**Buffer:** 5 hours distributed (scope cuts listed per day).

---

## Day 1 — Scanner + Scaffolding (9h)

### Goal: `peek scan .` walks any repo and reports what it found.

### Tasks

| # | Task | Hours | Details |
|---|---|---|---|
| 1.1 | Scaffold repo + `pyproject.toml` | 1.0 | `uv init` or `poetry init` → `pyproject.toml` with `typer`, `rich`, `textual`, `pathspec`; `peek/__init__.py`, `peek/cli.py` stub, `tests/` |
| 1.2 | `.gitignore` handling | 1.5 | `pathspec` — load `.gitignore`, `.peekignore`, default ignores (`__pycache__`, `.git`, `.venv`, `node_modules`, `dist`, `build`, `.pytest_cache`, `*.pyc`); test with real repos |
| 1.3 | File walker | 2.0 | `scanner.scan(path)` → `ScanResult`: walk, collect `FileInfo(path, size, ext, loc)`, count LOC (simple: non-empty lines minus comments heuristic), language breakdown; benchmark on 500-file repo |
| 1.4 | Tech stack detection | 1.5 | Check for `pyproject.toml`, `requirements.txt`, `package.json`, `Cargo.toml`, `go.mod`, `Dockerfile`, `Makefile`, `py.typed`, etc. → `TechStack` dict; parse `pyproject.toml` for deps |
| 1.5 | Entry point detection | 2.0 | Heuristics: filename (`main.py`, `app.py`, `cli.py`, etc.), `if __name__ == "__main__"`, `pyproject.toml [project.scripts]`, `Dockerfile CMD`; return ranked `EntryPoint` list |
| 1.6 | CLI stub + manual test | 1.0 | `peek scan .` command that prints `ScanResult` as Rich table; test on 3 repos (tiny fixture, `requests`, your own) |

### Code sketch — scanner

```python
# peek/scanner.py
from dataclasses import dataclass
from pathlib import Path
import pathspec

DEFAULT_IGNORE = ["__pycache__", ".git", ".venv", "node_modules", "dist", "build"]

@dataclass
class FileInfo:
    path: Path
    ext: str
    loc: int
    size: int

@dataclass
class ScanResult:
    files: list[FileInfo]
    tech_stack: dict
    entry_candidates: list[Path]
    stats: dict  # {total_files, total_loc, by_lang: {...}}

def scan(root: Path) -> ScanResult: ...
def detect_tech_stack(root: Path, files: list[FileInfo]) -> dict: ...
def detect_entry_points(root: Path, files: list[FileInfo]) -> list[Path]: ...
```

### EOD check

```bash
peek scan .                    # works on current repo
peek scan /tmp/some-other-repo # works on any path
# Output: Rich table with file count, LOC, tech stack, entry points
```

### Scope cuts if behind

- Drop LOC accuracy (use file size proxy)
- Drop `pyproject.toml` script parsing (just filename heuristics)

---

## Day 2 — Analyzer (10h)

### Goal: `peek analyze .` builds import graph, ranks files, generates summary.

### Tasks

| # | Task | Hours | Details |
|---|---|---|---|
| 2.1 | AST import extraction | 2.5 | `ast.parse` each `.py` file → `Import`/`ImportFrom` → resolve to local files vs external deps; handle `from . import`, relative imports, `__all__`; skip `SyntaxError` files gracefully |
| 2.2 | Graph construction | 2.0 | `dict[Path, set[Path]]` — `file → {imported_local_files}`; also `reverse_graph` for in-degree; handle `__init__.py` package imports |
| 2.3 | Centrality + ranking | 2.0 | In-degree + simple PageRank (5 iterations) + entry bonus; `rank_files(graph, entry_candidates)` → sorted `RankedFile(path, score, reason)`; test ranking on known repos (does `main.py` rank top?) |
| 2.4 | Heuristic summary | 1.5 | Template-based: detect framework (`fastapi`/`django`/`flask`/`click`/`typer` in imports), DB (`sqlalchemy`/`psycopg2`), queue (`celery`/`rq`), etc. → sentence; fallback to "Python project with N modules" |
| 2.5 | Wire scan → analyze → CLI | 1.0 | `peek analyze .` prints ranked list + summary as Rich; `AnalyzerResult` dataclass |
| 2.6 | Test on 3 real repos | 1.0 | Clone `requests`, `fastapi`, `textual` → verify ranking makes sense; fix edge cases (circular imports, namespace packages) |

### Code sketch — analyzer

```python
# peek/analyzer.py
from dataclasses import dataclass

@dataclass
class RankedFile:
    path: Path
    score: float
    reasons: list[str]  # ["entry point", "hub (imported by 5 files)"]

@dataclass
class AnalyzerResult:
    graph: dict[Path, set[Path]]
    ranked: list[RankedFile]
    summary: str
    tech_stack: dict

def build_graph(files: list[FileInfo], root: Path) -> dict[Path, set[Path]]: ...
def rank_files(graph, entry_candidates) -> list[RankedFile]: ...
def summarize(graph, ranked, tech_stack) -> str: ...
def analyze(scan_result: ScanResult) -> AnalyzerResult: ...
```

### EOD check

```bash
peek analyze . 
# Output:
# Summary: FastAPI-based API with Postgres...
# Start Here:
#   1. app/main.py (entry, hub) — score 9.2
#   2. app/core/executor.py (hub, central) — score 8.1
#   ...
```

### Scope cuts if behind

- Skip PageRank — use in-degree only (good enough for MVP)
- Skip framework detection — use generic summary template

---

## Day 3 — Renderer: Static + TUI (10h)

### Goal: `peek .` is beautiful. TUI is navigable.

### Tasks

| # | Task | Hours | Details |
|---|---|---|---|
| 3.1 | Rich static renderer | 3.0 | `renderer.render(result)` → 4 Rich panels: Summary, Architecture (ranked list as "graph"), Start Here (table), Stats/Stack; `Columns` layout; `--no-tui` flag; test in various terminal widths |
| 3.2 | ASCII mini-graph | 1.0 | `_ascii_graph.py`: `graph → "cli → api → core → db"` one-liner; or vertical `cli\n │\n api → core`; keep simple — ranked list IS the graph for MVP |
| 3.3 | Textual TUI skeleton | 2.5 | `tui.PeekApp(AnalyzerResult)` — layout: header + 4 panels + footer; mount Rich panels as `Static` widgets; key bindings: `q` quit, `j/k` nav |
| 3.4 | TUI interactivity | 2.5 | Navigate Start Here list; `enter` drills into file (show its imports/dependents); `o` opens `$EDITOR`; `/` filter; live summary update |
| 3.5 | Wire `peek .` (default = TUI, `--no-tui` = static) | 1.0 | `cli.py` — `peek [PATH]` → `scan` → `analyze` → `render` or `tui`; handle `--no-tui`/`--help`; test both modes |

### Code sketch — renderer + TUI

```python
# peek/renderer.py
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

def render_static(result: AnalyzerResult, console: Console): ...

# peek/tui.py
from textual.app import App
from textual.widgets import Static, ListView

class PeekApp(App):
    CSS = """..."""
    BINDINGS = [("q", "quit", "Quit"), ("o", "open", "Open"), ...]
    def compose(self): ...
    def on_key(self, event): ...
```

### EOD check

```bash
peek .              # TUI appears, navigable, beautiful
peek . --no-tui     # Static Rich output, pipeable
# Screenshot both — they should be tweet-ready
```

### Scope cuts if behind

- Drop drill-in (`enter`) — just nav + quit for MVP
- Drop `/` filter — add in P1
- Drop ASCII graph — Start Here list alone is enough

---

## Day 4 — Polish, P1 Features, Testing (9h)

### Goal: P1 features + robustness + tests.

### Tasks

| # | Task | Hours | Details |
|---|---|---|---|
| 4.1 | `--html` export | 1.5 | Render static output to self-contained HTML (Jinja template + Rich `export_html` or manual); `peek . --html -o peek.html` |
| 4.2 | `--pack` (smart LLM pack) | 2.0 | `peek . --pack` → concatenates ranked files (top N by score, within token budget) → clipboard (`pyperclip`) or stdout/file; respects token estimate (`tiktoken` or `len/4` heuristic); `peek . --pack --ask "auth"` filters by keyword |
| 4.3 | `--find "query"` | 1.0 | Keyword search over filenames + file contents (top 20 lines) ranked by `AnalyzerResult` score + keyword match; `peek --find "token validation"` |
| 4.4 | Optional LLM summary | 1.0 | `peek/llm.py` — if `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` set, call cheap model for better summary; fallback to heuristic; `peek . --llm` forces it |
| 4.5 | Tests | 2.0 | `tests/test_scanner.py`, `test_analyzer.py`, `test_renderer.py` — fixtures: 3 sample repos (tiny 5-file, medium 30-file, clone of `requests`); assert scan count, ranking, no crash on weird files |
| 4.6 | Edge cases + perf | 1.5 | Handle: non-Python repos (graceful), huge repos (2k+ files, timeout after 5s scan), binary files, `SyntaxError` files, empty repos, permission errors; benchmark < 2 sec for 500 files |

### EOD check

```bash
peek . --html -o /tmp/peek.html && open /tmp/peek.html
peek . --pack | wc -c
peek --find "auth" .
pytest -q  # all green
```

### Scope cuts if behind

- Drop `--find` (keyword search is nice but not P0)
- Drop LLM summary (heuristic is fine for v0.1.0)
- Minimal tests (just smoke tests) — full suite in v0.1.1

---

## Day 5 — Packaging, Demo, Docs, Launch (8h)

### Goal: `pip install peek` works + GitHub repo is launch-ready.

### Tasks

| # | Task | Hours | Details |
|---|---|---|---|
| 5.1 | `pyproject.toml` polish + PyPI | 1.5 | Finalize `pyproject.toml` (metadata, `readme`, `keywords`, `classifiers`, `project.urls`, `project.scripts = {peek = "peek.cli:app"}`); `python -m build`; `twine check`; `twine upload` (test.pypi first); verify `pip install peek` in fresh venv |
| 5.2 | README — the landing page | 2.0 | GIF at top (see 5.3), one-liner + install + demo, features, usage, examples (`peek` on 3 famous repos with screenshots), comparison table, contributing; use `rich` README template; badges (PyPI, stars, license) |
| 5.3 | Demo GIF/video | 1.5 | Record with `vhs` (charmbracelet/vhs) or `asciinema` + `agg` or simple screen record; script: `git clone requests` → `peek .` → TUI nav → `peek . --no-tui` → `peek --find`; 15–20 sec, 800px wide, < 3MB; also static screenshot fallback |
| 5.4 | GitHub repo polish | 1.0 | `LICENSE` (MIT), `CONTRIBUTING.md` (minimal), `assets/` (GIF, screenshots), repo description + topics (`python`, `cli`, `tui`, `codebase`, `visualization`), pin README GIF |
| 5.5 | Launch posts (draft, don't publish yet) | 1.5 | HN Show HN post (title + body), Twitter thread (3 tweets + GIF), Reddit r/Python post, Product Hunt draft; see `08_launch_playbook.md` |
| 5.6 | Smoke test + tag release | 0.5 | Fresh machine/VM: `pipx install peek` → `peek .` on 2 repos → `peek --help`; `git tag v0.1.0 && git push --tags`; GitHub Release with notes |

### README skeleton

```markdown
<p align="center">
  <img src="assets/demo.gif" width="800" />
</p>

<h1 align="center">peek — htop for codebases</h1>
<p align="center">Understand any codebase in 5 seconds. <code>pip install peek && peek .</code></p>
<p align="center">
  <a href="https://pypi.org/project/peek/"><img src="https://img.shields.io/pypi/v/peek" /></a>
  <a href="https://github.com/you/peek"><img src="https://img.shields.io/github/stars/you/peek?style=social" /></a>
</p>

## Install

\`\`\`bash
pip install peek        # or: pipx install peek / uv tool install peek
\`\`\`

## Usage

\`\`\`bash
peek .                  # interactive TUI
peek . --no-tui         # static output (for screenshots/CI)
peek . --html -o map.html
peek --find "auth" .
\`\`\`
...
```

### EOD check — launch readiness

- [ ] `pip install peek` works in fresh venv on macOS + Linux
- [ ] `peek .` TUI beautiful on 80×24 and 120×40 terminals
- [ ] `peek . --no-tui` screenshot is tweet-ready
- [ ] `demo.gif` < 3MB, < 20 sec, autoplay, no audio needed
- [ ] README GIF visible without scrolling
- [ ] `pytest -q` green, `ruff check` clean
- [ ] GitHub Release `v0.1.0` created

### Launch timing

- **Don't launch Day 5 evening** — launch next morning (Tue–Thu 08:00 UTC) for HN max visibility. Use Day 5 evening to rest and draft posts.

---

## Risk Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Textual TUI bugs on some terminals | Medium | Ship `--no-tui` as primary demo fallback; TUI is progressive enhancement |
| AST parse fails on Python 2 / weird syntax | Medium | `try/except SyntaxError` → skip file, log warning, don't crash |
| Huge repo (5k+ files) slow | Low | Cap scan at 2k files for MVP, show "…and 3k more" |
| `peek` name taken on PyPI | Medium | Alternatives: `codepeek`, `peek-code`, `peekcode`, `repeek` — check on Day 1 morning |
| Scope creep (want to add everything) | High | Strict P0/P1/P2 — cut P2 ruthlessly; P1 is "if time" |

---

## Hour-by-Hour Summary

| Day | Hours | Cumulative |
|---|---|---|
| 1 | 9 | 9 |
| 2 | 10 | 19 |
| 3 | 10 | 29 |
| 4 | 9 | 38 |
| 5 | 8 | 46 |

**This is tight but realistic for all-day coding.** If you have a pair, Day 3–4 parallelize (one on TUI, one on `--pack`/`--html`).

---

*Next → `07_competitive_landscape.md` and `08_launch_playbook.md`.*


---
*Author: **Hariom Lohar** -- hariomlohar.new@gmail.com -- https://hariomlohardev.github.io/ -- 2026-08-10*

