# Project Details — `peek` : Understand Any Codebase in 5 Seconds

> **Tagline:** The `htop` for codebases.  
> **One-liner:** `pip install peek && peek .` turns any repo into a beautiful, interactive architecture map in 5 seconds.  
> **Elevator pitch (15 sec):** "You know how `htop` makes system state instantly visible? `peek` does that for code. Run it in any repo — even one you've never seen — and in 5 seconds you get a beautiful map of what it does, how it's structured, where to start, and what talks to what. No API key, no config. Just `peek .`"

---

## 1. Problem — The "Now What?" Moment

Every programmer hits this weekly:

```bash
git clone https://github.com/someone/awesome-project
cd awesome-project
ls          # 47 files, 12 dirs
cat README.md  # "A blazingly fast framework for..." (lies or outdated)
# Now what? Where is the entry point? What talks to what? Where do I start?
find . -name "*.py" | head -20   # wall of files
grep -r "main" --include="*.py" | head  # noisy, not helpful
# 25 minutes later... still confused
```

**This is not niche. It's universal:**
- Onboarding to a new team/repo
- Evaluating an open-source project (should I use this?)
- Returning to your own code after 3 months
- Reviewing a PR in an unfamiliar area
- Packing context for an LLM (what files matter?)

**Current solutions and why they fail:**

| Solution | Why it fails |
|---|---|
| `README` | Outdated, incomplete, no structure |
| `find` / `grep` / `tree` | Syntactic, not semantic; no ranking |
| IDE "go to definition" | Requires IDE setup; doesn't give overview |
| Sourcegraph | Heavy, enterprise, cloud, not local CLI |
| `gitingest` / `repomix` | Dumps all files as text — not a map, no ranking |
| GitHub file browser | Flat list, no relationships |
| Asking a teammate | Not always possible; doesn't scale |

**Cost:** 15–60 minutes wasted per new repo. For a dev who touches 2–3 new repos/week, that's 2–4 hours/week. For teams onboarding new hires, it's days.

---

## 2. Solution — `peek`

### What it is

A **local, zero-config, beautiful CLI/TUI** that answers 5 questions instantly:

1. **What does this repo do?** — 3-sentence summary (heuristic, no LLM needed)
2. **What's the structure?** — Interactive file tree with smart ranking ("start here" ⭐)
3. **What talks to what?** — Architecture map: modules → imports → dependencies (visual graph)
4. **Where are the entry points?** — Auto-detected (`main.py`, `app.py`, `__main__`, `cli.py`, `api.py`, `manage.py`, etc.)
5. **What should I read first?** — Ranked "start here" list (entry points + most-imported + most-central)

### How it looks (ASCII mock — actual is Rich/Textual beautiful)

```
  peek  v0.1.0  —  /home/you/awesome-project  (Python · 47 files · 4.2k LOC)

  ┌─ Summary ─────────────────────────────────────────────────────┐
  │ FastAPI-based task queue with Redis backend. Workers pull     │
  │ jobs from Redis, execute via pluggable executors, and report  │
  │ results to Postgres. CLI via Typer, config via Pydantic.     │
  └───────────────────────────────────────────────────────────────┘

  ┌─ Architecture ───────────────────┐  ┌─ Start Here ⭐ ───────────────┐
  │                                │  │ ⭐ app/main.py      (entry)    │
  │   cli ──→ api ──→ core ──→ db  │  │ ⭐ app/core/executor.py (hub)  │
  │    │       │        │           │  │    app/worker.py    (worker)   │
  │    └───────┴────────┴──→ redis  │  │    app/config.py    (config)   │
  │                                │  │    tests/test_exec.py          │
  └────────────────────────────────┘  └────────────────────────────────┘

  ┌─ Stats ────────────────────────┐  ┌─ Tech Stack ────────────────────┐
  │  Python  92%  ██████████████   │  │  FastAPI · Redis · Postgres    │
  │  YAML     5%  █                │  │  Typer · Pydantic · pytest     │
  │  12 dirs · 47 files · 4.2k LOC │  │  Docker · ruff · uv            │
  └────────────────────────────────┘  └────────────────────────────────┘

  [j/k] navigate  [enter] drill in  [o] open in $EDITOR  [p] pack for LLM  [q] quit
```

**Modes:**

| Command | What it does |
|---|---|
| `peek .` | Full interactive TUI (default) |
| `peek . --no-tui` | Static rich output (for CI / piping / screenshots) |
| `peek . --html` | Export interactive HTML map (shareable) |
| `peek . --pack` | Pack ranked files for LLM (like gitingest but smart) |
| `peek . --find "auth"` | Semantic find (ranks files by relevance to query) |
| `peek --help` | Beautiful help with examples |

### Design principles

1. **Zero config, zero friction** — `peek .` works with no API key, no config file, no setup. LLM features are opt-in.
2. **Beauty is a feature** — Every output is Rich/Textual gorgeous. Screenshots should make people stop scrolling.
3. **Speed is a feature** — < 2 seconds for repos up to 500 files; < 5 seconds for 2k files. Feels instant.
4. **Heuristics first, LLM optional** — 80% value offline via AST + heuristics; LLM adds polish (better summaries) if `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` is set.
5. **Don't be clever, be useful** — No over-engineering. File ranking via simple centrality; summaries via template + heuristics before LLM.

---

## 3. Why This One — Decision Rationale

From `03_candidate_projects.md`, `peek` scored **90/100**, highest of 15. But scores alone don't capture the full thesis:

### The 5 tests `peek` passes that others don't

| Test | `peek` | `wtf` (2nd) | `packit` (3rd) |
|---|---|---|---|
| **Instant wow GIF?** | ✅ Map animating from chaos to clarity | ✅ Traceback before/after | ⚠️ File picker — good not great |
| **Every dev, every week?** | ✅ Every repo clone/onboarding | ✅ Every crash, but crashes are less frequent than new repos | ⚠️ Only AI coders (still ~70% in 2026) |
| **Zero-config?** | ✅ Heuristics offline | ✅ Heuristics offline | ❌ Needs embedding model download |
| **Weak competition?** | ✅ No beautiful local codebase map exists | ⚠️ `rich` traceback exists | ❌ gitingest/repomix already viral |
| **Screenshot shareable?** | ✅ Map of any repo is shareable | ✅ Traceback side-by-side | ❌ Clipboard action is invisible |

### The "platform" advantage

`peek` is not a one-trick tool — it's a **platform for codebase understanding**. Every runner-up becomes a `peek` feature:

- `wtf` → `peek --explain traceback.txt`
- `packit` → `peek --pack --ask "where is auth?"`
- `findit` → `peek --find "auth validation"`
- `depcruise` → `peek --deps`
- `lumen` → `peek --trace app.py` (future)

This gives `peek` a **compounding viral surface area**: each feature adds a new shareable moment and a new search keyword that leads to `peek`.

### The timing

- **AI coding is now default** (2026): every dev needs to understand code quickly, whether human or AI-written.
- **Textual is mature**: we can build a showcase TUI that itself goes viral as a Textual example.
- **No dominant tool exists**: Sourcegraph is heavy/enterprise; `tree`/`grep` are dumb; gitingest is not visual. The "htop for codebases" slot is empty.
- **Aug–Sep launch window**: peak "try new tools" season, before holiday noise.

---

## 4. Architecture

### High-level

```
┌─────────────────────────────────────────────────────────────┐
│                        peek CLI                             │
│  (Typer + Rich)  —  `peek .` / `peek . --html` / etc.     │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   ┌─────────┐   ┌──────────┐   ┌──────────┐
   │ Scanner │   │ Analyzer │   │ Renderer │
   │         │   │          │   │          │
   │ • walk  │──→│ • AST    │──→│ • Rich   │
   │ • .git- │   │ • graph  │   │ • Textual│
   │   ignore│   │ • rank   │   │ • HTML   │
   │ • LOC   │   │ • summary│   │ • JSON   │
   └─────────┘   └──────────┘   └──────────┘
        │              │              │
        └──────────────┼──────────────┘
                       ▼
              ┌─────────────────┐
              │  Optional LLM   │
              │  (summary boost)│
              │  OpenAI/Anthropic│
              └─────────────────┘
```

### Components (5-day scope)

#### A. Scanner (`peek/scanner.py` — ~150 lines)

- Walk `path` respecting `.gitignore` (via `pathspec`), `.peekignore`, default ignores (`__pycache__`, `.git`, `node_modules`, `.venv`, `dist`, `build`)
- Collect: file paths, sizes, extensions, LOC (via `pygount` or simple line count)
- Detect: language breakdown, tech stack (via file presence: `pyproject.toml` → Python, `package.json` → JS, `Cargo.toml` → Rust, `requirements.txt`, `Dockerfile`, `Makefile`, etc.)
- Detect: entry points (heuristics — see below)
- Output: `ScanResult(files, stats, tech_stack, entry_candidates)`

**Entry point heuristics (ranked):**
1. Files named `main.py`, `app.py`, `cli.py`, `manage.py`, `server.py`, `api.py`, `__main__.py`
2. Files with `if __name__ == "__main__"` or `def main(` at top level
3. `pyproject.toml [project.scripts]` / `[tool.poetry.scripts]`
4. `Dockerfile CMD` / `ENTRYPOINT`
5. Most-imported file that is not a utility

#### B. Analyzer (`peek/analyzer.py` — ~300 lines)

- **AST parsing** (Python files): `ast.parse` → extract `Import` / `ImportFrom` → build directed graph `file → imports`
- **Non-Python files**: heuristic edges (e.g., `package.json` dependencies, `Dockerfile` base images) — simple, not deep
- **Graph analysis** (no `networkx` required for MVP — simple dict + centrality):
  - In-degree (how many files import this) → "hub" score
  - Out-degree (how many this imports) → "leaf" vs "orchestrator"
  - PageRank-lite (iterative) → "centrality" for ranking
- **Ranking — "Start Here"** (weighted):
  - Entry point bonus ×3
  - In-degree (hub) ×2
  - Centrality ×1.5
  - File size penalty (prefer smaller entry files over huge utils)
  - Depth penalty (prefer top-level over deep nested)
- **Summary** (offline heuristic, no LLM):
  - Template: `"{Framework}-based {domain} with {backend}. {Workers/components} handle {action} via {mechanism}. {CLI/config} via {tools}."`
  - Inferred from: framework imports (`fastapi` → "FastAPI-based"), DB imports (`psycopg2`/`sqlalchemy` → "Postgres"), queue (`redis`/`celery` → "task queue"), etc.
  - Fallback: "Python project with {N} modules, entry at {file}."

#### C. Renderer (`peek/renderer.py` + `peek/tui.py` — ~400 lines)

- **Static mode** (`--no-tui`): Rich panels — Summary, Architecture (ASCII graph), Start Here, Stats, Tech Stack. Uses `rich.panel`, `rich.table`, `rich.tree`, `rich.columns`.
- **TUI mode** (default, `textual`):
  - Layout: header (path + stats) + 4 panels (Summary, Graph, Start Here, Stack) + footer (key hints)
  - Interactions: `j/k` or arrows navigate Start Here list; `enter` drills into file (shows its imports/dependents); `o` opens in `$EDITOR`; `p` packs for LLM; `/` filters; `q` quits
  - Graph: simple box-and-arrow ASCII art in a Rich panel (not full graphviz — just `cli → api → core → db` style). For MVP, a ranked list IS the graph; visual edges are v2.
- **HTML export** (`--html`): Render static output to self-contained HTML (Rich's `export_html` or simple Jinja template) — shareable.

#### D. Optional LLM Enhancer (`peek/llm.py` — ~100 lines)

- Only if `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` env var exists (or `peek --llm`)
- Prompt: "Summarize this codebase in 2–3 sentences given: file list, import graph, entry points, tech stack: {context}"
- Model: `gpt-4o-mini` or `claude-3-5-haiku` (cheap, fast)
- Graceful fallback: heuristic summary if no key or API fails
- **Never blocks main flow** — LLM call is async/optional, result replaces heuristic summary when ready (TUI updates live)

#### E. CLI (`peek/cli.py` — ~150 lines)

- `Typer` app with commands/options:
  ```
  peek [PATH] [--no-tui] [--html] [--pack] [--find QUERY] [--llm] [--json]
  ```
- Handles: path resolution, scan → analyze → render pipeline, error handling, `--help` with examples
- Entry point: `peek = "peek.cli:app"` in `pyproject.toml`

### Dependencies (minimal)

```toml
dependencies = [
    "typer>=0.12",        # CLI
    "rich>=13.0",         # Beautiful output
    "textual>=0.80",      # TUI
    "pathspec>=0.12",     # .gitignore
    "pygments>=2.17",     # Syntax (via rich)
]
# Optional:
# "openai>=1.0" / "anthropic>=0.30" — only if user wants LLM summary
# No networkx, no heavy ML — keep install < 10s
```

### Repo structure

```
peek/
├── pyproject.toml
├── README.md              # GIF + install + demo — the landing page
├── peek/
│   ├── __init__.py
│   ├── cli.py             # Typer app
│   ├── scanner.py         # File walk + tech detect
│   ├── analyzer.py        # AST graph + ranking + summary
│   ├── renderer.py        # Rich static renderer
│   ├── tui.py             # Textual TUI
│   ├── llm.py             # Optional LLM summary
│   └── _ascii_graph.py    # Tiny graph → ASCII art
├── tests/
│   ├── test_scanner.py
│   ├── test_analyzer.py
│   └── fixtures/          # 3 sample repos (tiny, medium, real)
├── assets/
│   ├── demo.gif           # THE GIF — 15 sec, above the fold
│   ├── screenshot.png     # Static fallback
│   └── architecture.png   # Diagram for README
└── scripts/
    └── record_demo.py     # Reproducible demo recording
```

---

## 5. MVP Features (v0.1.0 — Day 5)

### Must-have (P0 — ship without these is failure)

| # | Feature | Why P0 |
|---|---|---|
| 1 | `peek .` scans any repo respecting `.gitignore` | Core — without this nothing works |
| 2 | AST import graph for Python files | Core intelligence |
| 3 | "Start Here" ranked list (entry + hub + centrality) | The #1 user question, answered |
| 4 | Beautiful static output (`--no-tui`) with Rich | Shareable, screenshot-worthy, works everywhere |
| 5 | Interactive TUI (`textual`) with nav + drill-in | The wow factor, HN GIF material |
| 6 | Heuristic summary (no LLM) | Works offline, zero friction |
| 7 | Tech stack detection | Instant context |
| 8 | `pip install peek` in < 10s, no config | Viral prerequisite |

### Should-have (P1 — add if time on day 4–5)

| # | Feature | Notes |
|---|---|---|
| 9 | `--html` export | Shareable map for teams |
| 10 | `--pack` — smart LLM pack (ranked files → clipboard/file) | Gitingest-killer feature |
| 11 | Optional LLM summary (if API key) | Better summaries, opt-in |
| 12 | `--find "query"` keyword search ranked by relevance | Lightweight semantic-ish |
| 13 | File size / LOC stats + language breakdown | Easy, visual |

### Nice-to-have (P2 — v0.2.0)

| # | Feature | Notes |
|---|---|---|
| 14 | Full import graph visualization (graphviz/DOT) | Visual edges, not just list |
| 15 | True semantic search via embeddings | Needs model download — heavier |
| 16 | `peek --explain traceback.txt` | Absorb `wtf` |
| 17 | Watch mode (`peek --watch`) | Live update on file change |
| 18 | Config file (`.peek.toml`) | Custom entry hints, ignore rules |

---

## 6. Non-Goals (v0.1.0 explicitly does NOT do)

- ❌ Not a code editor or IDE — no editing, just understanding
- ❌ Not a linter/formatter — no style opinions
- ❌ Not a full semantic search engine — keyword + ranking only for MVP
- ❌ Not a replacement for `gitingest` for non-Python repos — Python-first, but handles other files gracefully
- ❌ No backend, no telemetry, no account, no cloud

---

## 7. Success Metrics (first 30 days)

| Metric | Target | How to measure |
|---|---|---|
| GitHub stars | 1k in week 1, 5k in month 1 | GitHub insights |
| `pip` downloads | 10k in month 1 | PyPI stats |
| HN front page | Top 10 for ≥ 4h | HN rank tracker |
| Demo GIF views | 50k impressions | Twitter analytics |
| Issues/PRs | 20+ community interactions | GitHub issues |
| "I used peek on X" tweets | 30+ organic | Twitter search |

---

*Next → `05_why_this_will_go_viral.md` — the viral thesis as a standalone memo.*


---
*Author: **Hariom Lohar** -- hariomlohar.new@gmail.com -- https://hariomlohardev.github.io/ -- 2026-08-10*

