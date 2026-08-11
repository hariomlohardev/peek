# plan.md — `peek` : Full 5-Day Build Plan (Day 1 → Launch)

> **Project:** `peek` — htop for codebases  
> **One-liner:** `pip install peek && peek .` → beautiful map of any repo in 5 seconds  
> **Stack:** Python + Rich + Textual + AST (no backend, no API key needed)  
> **Time:** 5 days × 10-12h/day = ~46h · **LOC:** ~1,000 · **Team:** 1 person  
> **Result:** PyPI package + GitHub repo + demo GIF + launch posts  
> **Portfolio:** https://hariomlohardev.github.io/

---

## 0. Before Day 1 — Setup (2 hours, do this tonight)

### What to install

```bash
# 1. Python 3.11+ (check: python --version)
python --version  # need 3.11+

# 2. Tools
pip install uv              # faster pip (optional but recommended)
pip install build twine     # for PyPI publishing
pip install ruff            # linter (optional)

# 3. Check name on PyPI (do FIRST — if taken, rename now)
pip index versions peek          # if taken, use: codepeek / peek-code / repeek
# Alternatives in order: peek > codepeek > peek-code > repeek

# 4. GitHub repo (create empty, don't push yet)
# Go to github.com/new → name: peek → Public → MIT License → Create
```

### Tech stack — what to use and why

| Tool | What it does | Why this one |
|---|---|---|
| **Python 3.11+** | Language | Your audience is Python devs, AST is native |
| **Typer** | CLI (`peek .`, `peek --help`) | Best CLI lib, auto --help, minimal boilerplate |
| **Rich** | Beautiful terminal output | Makes every output screenshot-worthy |
| **Textual** | Interactive TUI (`peek .`) | Rich's sister — showcase TUI, the wow factor |
| **pathspec** | `.gitignore` handling | Respects .gitignore correctly |
| **pyperclip** | Copy to clipboard (`--pack`) | For `peek --pack` feature |
| **openai / anthropic** | Optional LLM summary | Only if user has API key — never required |

**No heavy deps:** No networkx, no ML models, no database. Keep `pip install peek` under 10 seconds.

### Project structure to create on Day 1 morning

```
peek/
├── pyproject.toml
├── README.md
├── LICENSE (MIT)
├── .gitignore
├── peek/
│   ├── __init__.py        # version = "0.1.0"
│   ├── cli.py             # Typer app — entry point
│   ├── scanner.py         # File walk + tech stack + entry points
│   ├── analyzer.py        # AST graph + ranking + summary
│   ├── renderer.py        # Rich static output
│   ├── tui.py             # Textual TUI
│   ├── llm.py             # Optional LLM summary (Day 4)
│   └── _ascii_graph.py    # Tiny graph → ASCII helper
├── tests/
│   ├── test_scanner.py
│   ├── test_analyzer.py
│   └── fixtures/          # 3 sample repos (create Day 1)
├── assets/
│   ├── demo.gif           # Record on Day 5
│   └── screenshot.png
└── scripts/
    └── record_demo.py
```

### `pyproject.toml` — create this Day 1

```toml
[project]
name = "peek"  # or codepeek if peek taken
version = "0.1.0"
description = "The htop for codebases — understand any repo in 5 seconds"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
authors = [{name = "Hari Om Lohar", email = "your@email.com"}]
keywords = ["cli", "tui", "codebase", "visualization", "developer-tools", "textual", "rich"]
classifiers = [
    "Programming Language :: Python :: 3",
    "Environment :: Console",
    "Topic :: Software Development",
]
dependencies = [
    "typer>=0.12",
    "rich>=13.0",
    "textual>=0.80",
    "pathspec>=0.12",
]
[project.urls]
Homepage = "https://github.com/YOUR_USERNAME/peek"
Repository = "https://github.com/YOUR_USERNAME/peek"

[project.scripts]
peek = "peek.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

## Day 1 — Scanner (9 hours)

**Goal by EOD:** `peek scan .` prints file stats + tech stack + entry points for any repo.

| # | Task | Hours | What to do |
|---|---|---|---|
| 1.1 | Scaffold | 1h | Create structure above, `pyproject.toml`, `peek/__init__.py`, `peek/cli.py` stub with `typer.Typer()`, `pip install -e .` and test `peek --help` works |
| 1.2 | .gitignore | 1.5h | Use `pathspec`: load `.gitignore` + default ignores (`__pycache__`, `.git`, `.venv`, `node_modules`, `dist`, `build`, `.pytest_cache`, `*.pyc`) + `.peekignore`. Test on real repos (clone `requests`) |
| 1.3 | File walker | 2h | `scanner.py`: `scan(root: Path) -> ScanResult` — walk, collect `FileInfo(path, ext, loc, size)`, count LOC (non-empty lines), language breakdown. Benchmark on 500-file repo — must be <1 sec |
| 1.4 | Tech stack | 1.5h | `detect_tech_stack()` — check for `pyproject.toml`, `requirements.txt`, `package.json`, `Cargo.toml`, `Dockerfile`, `Makefile` → dict. Parse `pyproject.toml` for deps |
| 1.5 | Entry points | 2h | `detect_entry_points()` — heuristics: (1) filename `main.py/app.py/cli.py/__main__.py`, (2) `if __name__ == "__main__"`, (3) `pyproject.toml [project.scripts]`, (4) `Dockerfile CMD`. Return ranked list |
| 1.6 | CLI + test | 1h | `peek scan .` prints Rich table. Test: `peek scan .` on current repo + `peek scan /tmp/requests` — must work on any path |

**EOD check:**
```bash
peek scan .                      # Rich table: files, LOC, tech, entries
peek scan /tmp/requests          # works on any repo
```

**If behind, cut:** LOC accuracy (use file size), `pyproject.toml` script parsing.

---

## Day 2 — Analyzer (10 hours)

**Goal by EOD:** `peek analyze .` builds import graph, ranks files, generates summary.

| # | Task | Hours | What to do |
|---|---|---|---|
| 2.1 | AST imports | 2.5h | `analyzer.py`: `ast.parse` each `.py` → `Import`/`ImportFrom` → resolve to local files vs external. Handle `from . import`, relative imports. Skip `SyntaxError` gracefully |
| 2.2 | Graph | 2h | `dict[Path, set[Path]]` — `file → {imported files}` + `reverse_graph` for in-degree. Handle `__init__.py` packages |
| 2.3 | Ranking | 2h | `rank_files()` — score = entry bonus ×3 + in-degree ×2 + PageRank-lite (5 iterations) ×1.5 - size/depth penalty. Return `RankedFile(path, score, reasons)`. Test: does `main.py` rank top? |
| 2.4 | Summary | 1.5h | `summarize()` — template: detect framework (`fastapi`→"FastAPI-based", `django`→"Django"), DB, queue → sentence. Fallback: "Python project with N modules, entry at X" |
| 2.5 | Wire CLI | 1h | `peek analyze .` prints ranked list + summary as Rich. `AnalyzerResult` dataclass |
| 2.6 | Test real repos | 1h | Clone `requests`, `fastapi`, `textual` → verify ranking makes sense, fix circular imports |

**EOD check:**
```bash
peek analyze .
# Summary: FastAPI-based API with Postgres...
# Start Here:
#   1. app/main.py (entry, hub) — 9.2
#   2. app/core/executor.py (hub) — 8.1
```

**If behind, cut:** PageRank (use in-degree only), framework detection (generic summary).

---

## Day 3 — Renderer: Static + TUI (10 hours) ⭐ Most important day

**Goal by EOD:** `peek .` is beautiful. This is the viral day.

| # | Task | Hours | What to do |
|---|---|---|---|
| 3.1 | Rich static | 3h | `renderer.py`: `render_static(result)` → 4 panels (Summary, Architecture, Start Here, Stats/Stack) using `rich.panel`, `rich.table`, `rich.columns`. `peek . --no-tui` must be tweet-ready |
| 3.2 | ASCII graph | 1h | `_ascii_graph.py`: `graph → "cli → api → core → db"` one-liner. Keep simple — ranked list IS the graph for MVP |
| 3.3 | TUI skeleton | 2.5h | `tui.py`: `class PeekApp(App)` — layout: header + 4 panels + footer, `q` quit, `j/k` nav. Mount Rich panels as `Static` widgets |
| 3.4 | TUI interactivity | 2.5h | Navigate Start Here list, `enter` drill into file (show imports/dependents), `o` open in `$EDITOR`, `/` filter |
| 3.5 | Wire `peek .` | 1h | `cli.py`: `peek [PATH]` → scan → analyze → render or TUI. Default = TUI, `--no-tui` = static. Test both |

**EOD check:**
```bash
peek .              # TUI appears, navigable, beautiful — screenshot this
peek . --no-tui     # Static output — also beautiful, pipeable
# Both must be tweet-ready at 80x24 and 120x40
```

**If behind, cut:** `enter` drill-in, `/` filter — just nav + quit for MVP.

---

## Day 4 — Polish + P1 Features + Tests (9 hours)

**Goal by EOD:** P1 features + tests + edge cases handled.

| # | Task | Hours | What to do |
|---|---|---|---|
| 4.1 | `--html` | 1.5h | `peek . --html -o map.html` — self-contained HTML (Jinja or Rich `export_html`) — shareable |
| 4.2 | `--pack` | 2h | `peek . --pack` — concatenates top-N ranked files within token budget → clipboard (`pyperclip`) or stdout. `peek . --pack --ask "auth"` filters by keyword. This is your gitingest-killer |
| 4.3 | `--find` | 1h | `peek --find "auth" .` — keyword search over filenames + content, ranked by analyzer score |
| 4.4 | LLM summary | 1h | `llm.py` — if `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` set, call cheap model for better summary. Never blocks main flow, fallback to heuristic |
| 4.5 | Tests | 2h | `tests/test_scanner.py`, `test_analyzer.py` — fixtures: tiny 5-file repo, medium 30-file repo, clone of `requests`. Assert scan count, ranking, no crash |
| 4.6 | Edge cases | 1.5h | Handle: non-Python repos (graceful), huge repos (cap at 2k files), binary files, `SyntaxError`, empty repos, permission errors. Benchmark: <2 sec for 500 files |

**EOD check:**
```bash
peek . --html -o /tmp/peek.html && open /tmp/peek.html
peek . --pack | wc -c
peek --find "auth" .
pytest -q  # all green
```

**If behind, cut:** `--find`, LLM summary (heuristic is fine for v0.1.0).

---

## Day 5 — Package, Demo, Docs, Launch Prep (8 hours)

**Goal by EOD:** `pip install peek` works + GitHub ready + launch posts drafted. **Don't launch today — launch tomorrow 08:00 UTC.**

| # | Task | Hours | What to do |
|---|---|---|---|
| 5.1 | PyPI publish | 1.5h | Finalize `pyproject.toml` metadata → `python -m build` → `twine check dist/*` → `twine upload --repository testpypi` test → `twine upload` real → verify `pip install peek` in fresh venv (test on 2 machines or Docker) |
| 5.2 | README | 2h | GIF at top (5.3), one-liner + install + usage in first 200px, features, comparison table, badges (PyPI, stars, MIT). Use template below |
| 5.3 | Demo GIF | 1.5h | Record with `vhs` (charmbracelet/vhs) or screen record + gifski. Script: `git clone requests` → `peek .` → TUI nav → `peek . --no-tui` → `peek --find`. 15-20 sec, 800px, <3MB, loops, no audio. Also static `screenshot.png` |
| 5.4 | GitHub polish | 1h | `LICENSE` (MIT), repo description: "The htop for codebases — understand any repo in 5 seconds", topics: `python cli tui textual rich codebase visualization developer-tools`, social preview image, pin repo |
| 5.5 | Launch posts | 1.5h | Draft (don't publish): HN Show HN post, X thread (3 tweets + GIF), Reddit r/Python post, Product Hunt draft. Use `08_launch_playbook.md` |
| 5.6 | Smoke test + tag | 0.5h | Fresh VM: `pipx install peek` → `peek .` on 2 repos → `peek --help` → `git tag v0.1.0 && git push --tags` → GitHub Release with notes + GIF |

### README template

```markdown
<p align="center">
  <img src="assets/demo.gif" width="800" />
</p>

<h1 align="center">peek — htop for codebases</h1>
<p align="center">Understand any codebase in 5 seconds. <code>pip install peek && peek .</code></p>
<p align="center">
  <a href="https://pypi.org/project/peek/"><img src="https://img.shields.io/pypi/v/peek" /></a>
  <img src="https://img.shields.io/github/stars/YOUR_USERNAME/peek?style=social" />
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
peek . --pack           # ranked files for LLM
\`\`\`

## Why peek?
[Comparison table + features]

## Portfolio
Built by Hari Om Lohar — https://hariomlohardev.github.io/
```

### EOD checklist

- [ ] `pip install peek` works in fresh venv (macOS + Linux)
- [ ] `peek .` TUI beautiful at 80×24 and 120×40
- [ ] `peek . --no-tui` screenshot tweet-ready
- [ ] `demo.gif` <3MB, <20 sec, autoplay
- [ ] README GIF visible without scrolling
- [ ] `pytest -q` green, `ruff check` clean
- [ ] GitHub Release `v0.1.0` created
- [ ] Launch posts drafted (not yet published)

---

## Day 6 — Launch Day (not a build day)

**Best days: Tuesday, Wednesday, or Thursday. If you finish Friday, wait until Tuesday.**

| Time (UTC) | What to do |
|---|---|
| 08:00 | **HN Show HN** — Title: `Show HN: peek — htop for codebases (understand any repo in 5 seconds)` — reply to every comment within 15 min for 2 hours |
| 08:30 | **X/Twitter** — 3-tweet thread + GIF, pin first tweet, tag @willmcgugan (Rich/Textual) |
| 10:00 | **Reddit r/Python** — same demo, tailored title |
| 12:00 | Monitor GitHub stars/issues — fix `pip install` breakage IMMEDIATELY |
| Day 2 | Product Hunt + newsletters (PyCoder's Weekly, TLDR) |
| 24-48h | Reply to every issue, tweet "peek hit X stars 🎉", triage PRs |

**Full launch playbook:** `08_launch_playbook.md` (hour-by-hour + copy-paste templates)

---

## Daily Commands Cheat Sheet

```bash
# Every morning
git pull
pip install -e .  # after pyproject changes

# Test during day
peek scan . && peek analyze . && peek . && peek . --no-tui
pytest -q && ruff check peek/

# End of day
git add -A && git commit -m "Day N: what you did"
git push

# Day 5 publish
python -m build && twine check dist/* && twine upload
pip install peek  # in fresh venv to verify
```

---

## If You Fall Behind — Scope Cuts (in order)

1. Cut `--find` (nice but not P0)
2. Cut LLM summary (heuristic is fine)
3. Cut `--html` (add in v0.1.1)
4. Cut TUI drill-in (just nav + quit)
5. Cut PageRank (use in-degree only)

**Never cut:** `peek .` beautiful output, `peek . --no-tui`, scanner, ranking, PyPI publish, demo GIF.

---

## Final Check — Are You Done?

You are done when:
- `pip install peek` works for a stranger in a fresh venv
- `peek .` on `requests` makes them say "whoa"
- README GIF stops scrolling
- `git tag v0.1.0` is pushed

Then wait 24h and launch 08:00 UTC Tue-Thu.

**You've got this. 5 days → viral dev tool → portfolio star.** 🔭

Portfolio: https://hariomlohardev.github.io/
