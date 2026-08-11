# Candidate Projects — 15 Ideas Scored for Viral × Feasible × Useful

> All 15 candidates were generated from 3 lenses (AI-augmented, DX/joy, universal pain) and scored on 4 axes. One winner is picked at the end.

---

## Scoring Rubric

Each candidate scored 1–10 on:

| Axis | Question |
|---|---|
| **Viral (V)** | Would you share this within 5 min of trying it? Is the demo GIF jaw-dropping? |
| **Feasible 5d (F)** | Can 1 person build a lovable MVP in 5 all-day sessions in Python? |
| **TAM (T)** | How many programmers hit this pain weekly? (10 = every dev, 1 = niche) |
| **Novelty (N)** | How underserved is it? (10 = no good solution, 1 = crowded) |

**Total = V × F × T × N** is not literal multiplication — we use weighted composite `Score = (V*0.35 + F*0.25 + T*0.25 + N*0.15)` scaled to 100. Rankings are what matter.

---

## Lens A — AI-Augmented Productivity (5 candidates)

### A1 — `context` / `packit` — Smart Codebase Packer for LLMs

| Field | Detail |
|---|---|
| **One-liner** | `packit . --ask "where is auth?"` → copies only relevant files to clipboard, token-counted |
| **Problem** | Pasting code into Claude/Cursor is manual, hits token limits, includes junk |
| **Solution** | AST + embeddings (local, via sentence-transformers) to find relevant files; TUI file picker with live token counter; `.gitignore`-aware; copy to clipboard |
| **Demo hook** | Split screen: manual copy-paste hell vs `packit --ask` in 2 sec |
| **Tech** | Python, `sentence-transformers` (all-MiniLM), `rich`, `pyperclip`, `tiktoken` |
| **Differentiator vs gitingest/repomix** | Question-aware retrieval + interactive TUI + live token budget |
| **Monetization** | Pro: team shared contexts, cloud history |
| **Scores** | V 8 · F 9 · T 10 · N 5 → **Composite 81** |
| **Verdict** | Strong, but crowded — gitingest/repomix already viral, need 10× to displace |

### A2 — `diffsense` — Semantic PR Explainer

| Field | Detail |
|---|---|
| **One-liner** | `diffsense` in a PR branch → beautiful terminal summary of what *actually* changed (not just lines) |
| **Problem** | GitHub diff is syntactic; reviewers miss semantic changes ("this refactors auth but breaks rate limiting") |
| **Solution** | Parse diff + AST diff + optional LLM to generate "what changed, why it matters, risks" summary |
| **Demo hook** | Ugly GitHub diff vs beautiful `diffsense` output with risk highlights |
| **Tech** | Python, `unidiff`, `tree-sitter`, `rich`, optional OpenAI API |
| **Scores** | V 7 · F 7 · T 8 · N 6 → **70** |
| **Verdict** | Useful but PR-specific — narrower TAM than codebase-wide |

### A3 — `aigen` — AI Test Generator That Doesn't Suck (Local)

| Field | Detail |
|---|---|
| **One-liner** | `aigen src/auth.py` → generates `tests/test_auth.py` with high-coverage pytest tests |
| **Problem** | Writing tests is hated; AI test generators exist but produce flaky/low-coverage tests |
| **Solution** | AST-aware prompt engineering + mutation testing to self-correct; generates only tests that pass locally before showing |
| **Demo hook** | `ls tests/` (empty) → `aigen` → `pytest` (all green, 85% coverage) |
| **Tech** | Python, `ast`, `coverage.py`, `mutmut` ideas, LLM API |
| **Scores** | V 7 · F 5 · T 9 · N 5 → **65** |
| **Verdict** | Hard to get quality right in 5 days — flaky demo kills viral |

### A4 — `promptlint` — Linter for LLM Prompts in Code

| Field | Detail |
|---|---|
| **One-liner** | `promptlint .` finds brittle prompts in your codebase and suggests robust rewrites |
| **Problem** | Prompts embedded in code are untested, unversioned, and break silently |
| **Solution** | Detect prompt strings (heuristic + AST), lint for anti-patterns, suggest improvements via LLM |
| **Demo hook** | "Found 12 prompts — 3 are brittle" with inline suggestions |
| **Tech** | Python, `ast`, `rich`, LLM API |
| **Scores** | V 5 · F 7 · T 5 · N 8 → **60** |
| **Verdict** | Too niche — only teams with heavy prompt usage feel it |

### A5 — `hallucatch` — Catches AI-Hallucinated APIs

| Field | Detail |
|---|---|
| **One-liner** | `hallucatch app.py` flags calls to non-existent APIs/packages that AI likely hallucinated |
| **Problem** | AI generates `import nonexistent_lib` or `client.fake_method()` that fails at runtime |
| **Solution** | Static analysis + PyPI index check + type stub awareness to flag hallucinated imports/calls |
| **Demo hook** | AI-generated file with 3 hallucinated calls → `hallucatch` highlights them in red |
| **Tech** | Python, `ast`, `importlib.metadata`, PyPI API, `rich` |
| **Scores** | V 6 · F 8 · T 7 · N 7 → **69** |
| **Verdict** | Clever, but hallucination rate is dropping as models improve — shrinking TAM |

---

## Lens B — Pure DX & Joy (5 candidates)

### B1 — `wtf` / `oops` / `autopsy` — Beautiful Traceback That Explains Itself

| Field | Detail |
|---|---|
| **One-liner** | `wtf python app.py` — any crash becomes a beautiful, plain-English explanation + fix suggestion |
| **Problem** | Python tracebacks are still cryptic; juniors stare at them, seniors waste time |
| **Solution** | Rich traceback + heuristic explainer (offline, no API key) + optional LLM deep-explain; `wtf --fix` applies patch |
| **Demo hook** | Side-by-side: CPython ugly traceback vs `wtf` beautiful explained output — night and day |
| **Tech** | Python, `rich`, `traceback`, `ast`, optional LLM |
| **Scores** | V 9 · F 9 · T 9 · N 6 → **84** |
| **Verdict** | **Strong runner-up.** Massive TAM, amazing demo, 5-day feasible. Weakness: `rich` traceback already exists, need to 10× it |

### B2 — `lumen` / `spy` — Inline Execution Visualizer

| Field | Detail |
|---|---|
| **One-liner** | `lumen app.py` — see variable values inline as code runs, no debugger, no print statements |
| **Problem** | `print()` debugging is manual; `pdb` is hostile; `snoop`/`icecream` not visual enough |
| **Solution** | `sys.settrace` hook that renders variable flow inline in terminal with colors/arrows; `lumen --watch x,y` |
| **Demo hook** | Mesmerizing GIF: code on left, values flowing on right, loop variables animating |
| **Tech** | Python, `sys.settrace`, `ast`, `rich`/`textual` |
| **Scores** | V 10 · F 6 · T 7 · N 7 → **77** |
| **Verdict** | Most visually viral, but `sys.settrace` edge cases (async, C extensions) make 5-day polish hard |

### B3 — `peek` / `atlas` / `cartographer` — Understand Any Codebase in 5 Seconds ⭐

| Field | Detail |
|---|---|
| **One-liner** | `peek .` → beautiful interactive architecture map of any repo in 5 seconds |
| **Problem** | Cloning a repo → "what does this do? where to start?" → 30 min of `find`/`grep`/`README` |
| **Solution** | AST import graph + file ranking + heuristic summarizer + Textual TUI; optional LLM summary; HTML export |
| **Demo hook** | `git clone k8s` → `peek .` → stunning map: modules, entry points, "start here" |
| **Tech** | Python, `ast`, `pathlib`, `rich`, `textual`, `networkx` (optional), LLM optional |
| **Scores** | V 10 · F 8 · T 10 · N 7 → **90** |
| **Verdict** | **WINNER.** Highest composite. Universal, visual, 5-day feasible, underserved. |

### B4 — `ship` / `commitcraft` — One-Command Ship: Commit + Push + PR

| Field | Detail |
|---|---|
| **One-liner** | `ship` — analyzes `git diff` → writes perfect commit message → pushes → creates PR with description |
| **Problem** | Writing commit messages and PR descriptions is daily toil, done poorly |
| **Solution** | `git diff` → heuristic + optional LLM → conventional-commit message + PR body; beautiful preview + `ship --yolo` |
| **Demo hook** | Messy diff → `ship` → beautiful commit + PR in 2 sec, side-by-side |
| **Tech** | Python, `gitpython`/`subprocess`, `rich`, LLM API |
| **Scores** | V 8 · F 9 · T 10 · N 4 → **79** |
| **Verdict** | Huge TAM, easy to build, but crowded (`aicommits`, `opencommit`, `commitgpt` exist — low novelty) |

### B5 — `dive` / `loglens` — Magical Log Tailer

| Field | Detail |
|---|---|
| **One-liner** | `dive app.log` — auto-detects log format, colorizes, filters, and explains errors inline |
| **Problem** | `tail -f` is dumb; logs are unstructured; finding errors is manual grep |
| **Solution** | Heuristic log parser + pattern detection + error highlighting + `dive --errors-only` + time histogram |
| **Demo hook** | Wall of grey logs vs `dive` — errors pop in red, histogram at bottom |
| **Tech** | Python, `rich`, `textual`, regex heuristics |
| **Scores** | V 7 · F 8 · T 7 · N 6 → **71** |
| **Verdict** | Useful for backend/devops niche, less universal than `peek` |

---

## Lens C — Universal Workflow Pain (5 candidates)

### C1 — `envdoctor` — Python Env Doctor & Fixer

| Field | Detail |
|---|---|
| **One-liner** | `envdoctor --fix` — diagnoses and fixes venv/pip/python version issues automatically |
| **Problem** | "Works on my machine" + cryptic pip errors + venv confusion wastes hours |
| **Solution** | Scan `pyproject.toml`, `requirements*.txt`, `venv`, `python --version`, `pip check` → diagnose + auto-fix |
| **Demo hook** | Broken env with 5 errors → `envdoctor` → "Fixed 4/5, here's the last one" |
| **Tech** | Python, `packaging`, `importlib.metadata`, `subprocess`, `rich` |
| **Scores** | V 6 · F 8 · T 8 · N 6 → **70** |
| **Verdict** | High pain but demo is not visually viral — hard to GIF |

### C2 — `findit` — Semantic Code Search ("find function by what it does")

| Field | Detail |
|---|---|
| **One-liner** | `findit "where is auth token validated"` → finds relevant code by intent, not keyword |
| **Problem** | `grep -r` is keyword-only; you need to know the function name to find it |
| **Solution** | Local embeddings of code chunks (docstrings + names + bodies) via `sentence-transformers`; `findit "query"` → ranked results |
| **Demo hook** | `grep "auth"` (10 noisy hits) vs `findit "auth token validated"` (1 perfect hit) |
| **Tech** | Python, `sentence-transformers`, `ast`, `rich` |
| **Scores** | V 7 · F 7 · T 9 · N 7 → **75** |
| **Verdict** | Strong, but embedding setup adds friction (model download); could be a `peek` feature instead |

### C3 — `mockit` — Instant API Mock Server

| Field | Detail |
|---|---|
| **One-liner** | `mockit --record https://api.example.com` captures traffic → `mockit --serve` serves mocks locally |
| **Problem** | Frontend/dev without backend, testing without staging, flaky external APIs |
| **Solution** | HTTP proxy recorder + FastAPI mock server from OpenAPI or captured traffic |
| **Demo hook** | Real API call → `mockit` records → offline mock serves instantly |
| **Tech** | Python, `FastAPI`, `httpx`, `mitmproxy` concepts |
| **Scores** | V 7 · F 6 · T 7 · N 5 → **64** |
| **Verdict** | Crowded (msw, wiremock, prism) — hard to differentiate in 5 days |

### C4 — `depcruise` / `depgraph` — Beautiful Dependency Visualizer

| Field | Detail |
|---|---|
| **One-liner** | `depcruise .` → interactive dependency graph of your Python project (imports + pip deps) |
| **Problem** | `pipdeptree` is text-only; import cycles and bloat are invisible |
| **Solution** | AST imports + `importlib.metadata` → graph with cycle detection, bloat highlights, `depcruise --why package` |
| **Demo hook** | `pipdeptree` (wall of text) vs `depcruise` (beautiful interactive graph, cycles in red) |
| **Tech** | Python, `ast`, `networkx`, `rich`/`textual`, `graphviz` optional |
| **Scores** | V 7 · F 8 · T 7 · N 6 → **71** |
| **Verdict** | Could be a killer *feature* of `peek`, but standalone is narrower |

### C5 — `gitlens-lite` — Git History Visualizer for Humans

| Field | Detail |
|---|---|
| **One-liner** | `gl file.py` — see who changed what, when, why — beautifully, in terminal |
| **Problem** | `git log`/`blame` are hostile; understanding file history is painful |
| **Solution** | `git log --follow` + `blame` → rich timeline, author viz, "why was this line added?" |
| **Demo hook** | `git log --oneline` (wall of hashes) vs `gl` (colored timeline with messages) |
| **Tech** | Python, `gitpython`/`subprocess`, `rich` |
| **Scores** | V 6 · F 8 · T 7 · N 5 → **65** |
| **Verdict** | `lazygit`/`gitui` already cover this well enough |

---

## Composite Ranking — Top 15

| Rank | ID | Name | One-liner | V | F | T | N | Composite | Tier |
|---|---|---|---|---|---|---|---|---|---|
| **1** | **B3** | **`peek`** | **Understand any codebase in 5 sec** | 10 | 8 | 10 | 7 | **90** | **🏆 Winner** |
| 2 | B1 | `wtf` | Beautiful traceback that explains itself | 9 | 9 | 9 | 6 | 84 | Runner-up |
| 3 | A1 | `packit` | Smart codebase packer for LLMs | 8 | 9 | 10 | 5 | 81 | Runner-up |
| 4 | B4 | `ship` | One-command commit+push+PR | 8 | 9 | 10 | 4 | 79 | Strong |
| 5 | B2 | `lumen` | Inline execution visualizer | 10 | 6 | 7 | 7 | 77 | Visual king, hard |
| 6 | C2 | `findit` | Semantic code search | 7 | 7 | 9 | 7 | 75 | Feature of peek |
| 7 | A2 | `diffsense` | Semantic PR explainer | 7 | 7 | 8 | 6 | 70 | Narrow |
| 7 | C1 | `envdoctor` | Env doctor & fixer | 6 | 8 | 8 | 6 | 70 | Not viral |
| 9 | B5 | `dive` | Magical log tailer | 7 | 8 | 7 | 6 | 71 | Niche |
| 9 | C4 | `depcruise` | Dependency visualizer | 7 | 8 | 7 | 6 | 71 | Feature of peek |
| 11 | A5 | `hallucatch` | Catches hallucinated APIs | 6 | 8 | 7 | 7 | 69 | Shrinking |
| 12 | C3 | `mockit` | Instant mock server | 7 | 6 | 7 | 5 | 64 | Crowded |
| 12 | A3 | `aigen` | AI test generator | 7 | 5 | 9 | 5 | 65 | Flaky demo |
| 14 | C5 | `gitlens-lite` | Git history viz | 6 | 8 | 7 | 5 | 65 | Covered |
| 15 | A4 | `promptlint` | Prompt linter | 5 | 7 | 5 | 8 | 60 | Niche |

### Why `peek` won — the 4-way test

| Test | `peek` | Next best (`wtf`) | `packit` |
|---|---|---|---|
| **Is demo GIF jaw-dropping?** | ✅ Architecture map animating | ✅ Traceback before/after | ⚠️ TUI file picker — good not great |
| **Does every dev feel this weekly?** | ✅ Every repo clone/onboarding | ✅ Every crash | ✅ Every AI coding session |
| **Can it work with zero config?** | ✅ `peek .` — no API key needed | ✅ Offline heuristics | ⚠️ Needs embeddings download |
| **Is competition weak?** | ✅ No beautiful local codebase map | ⚠️ `rich` traceback exists | ❌ gitingest/repomix already viral |
| **Shareability** | ✅ Screenshot of any repo's map | ✅ Side-by-side traceback | ⚠️ Clipboard action — invisible |

**`peek` is the only candidate that scores ✅ on all five.**

---

## What to do with runners-up

Don't discard — **absorb them as `peek` features** (post-MVP):

| Runner-up | How it becomes a `peek` feature |
|---|---|
| `wtf` traceback | `peek --explain traceback.txt` |
| `packit` smart packer | `peek --pack --ask "where is auth?"` |
| `findit` semantic search | `peek --find "auth validation"` |
| `depcruise` deps | `peek --deps` |
| `ship` commit | `peek` already maps repo → helps write better commits |

This makes `peek` a **platform** for codebase understanding, not a one-trick tool — compounding viral surface area.

---

*Next → `04_project_details__peek.md` — the full spec for the winner.*


---
*Author: **Hariom Lohar** -- hariomlohar.new@gmail.com -- https://hariomlohardev.github.io/ -- 2026-08-10*

