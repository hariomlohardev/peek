# Contributing to peek

Thanks for wanting to contribute! `peek` is a small, fast, zero-config codebase — we keep the bar high for simplicity.

> **New here?** Start with a **Good First Issue** — browse the open ones (they rank high on GitHub search and get priority review):
>
> <a href="https://github.com/hariomlohardev/peek/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22"><img src="https://img.shields.io/github/issues/hariomlohardev/peek/good%20first%20issue?label=good%20first%20issues&color=7057ff" alt="Good First Issues"/></a>
>
> **Browse:** https://github.com/hariomlohardev/peek/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22
>
> - **Good First Issues (beginner):** docstrings, `peek wtf --help` example, `peek --version` test — perfect for first PR
> - **Intermediate (60-90 min):** `tiktoken`, `peek diff`, `peek serve`
> - **Complex (1-2 days):** `peek-mcp`, polyglot, `peek-vscode`

## Quick Start

Requires Python 3.11+.

Create and activate a virtual environment:

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# PowerShell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
```

Install from the Git root (the package directory is `peek/`):

```bash
git clone https://github.com/YOUR-USERNAME/peek && cd peek
python -m pip install -e "./peek[dev]"
```

Change into `peek/` before running tests, lint, or the demo generator:

```bash
cd peek
python -m pytest -q
ruff check peek
# optional demo: python -m peek.tools.gen_demo
```

To contribute: fork the repo, clone your fork, create a branch (`git checkout -b fix/thing`), make changes, and open a PR to upstream `main`.

## How to Contribute

1. **Fork** and create a branch: `git checkout -b fix/thing` or `feat/thing`
2. **Code**: keep it under ~200 LOC per file, handle edge cases (binary, huge, SyntaxError, empty, non-python)
3. **Test**: add a test in `peek/tests/` — fixtures in temp dirs, no network, no `git clone` in tests
4. **Style**: `ruff check peek` (line length 100), `ruff format --check peek`, `pytest -q` must pass
5. **PR**: clear title, what/why, screenshot if you touch renderer/TUI

## Project Structure

```
peek/peek/
  scanner.py      — walk + .gitignore + LOC + tech stack + entry
  analyzer.py     — AST graph + PageRank + ranking + summary (now polyglot JS/TS)
  symbols.py      — symbol index (def/class) via ast + JS regex
  embeddings.py   — BM25 + fastembed semantic index for find/pack
  graph.py        — DOT/SVG/HTML export (peek graph)
  git.py          — git log/diff/hot/blame (peek diff/log/hot)
  renderer.py     — Rich static panels + build_html
  _ascii_graph.py — one-liner graph
  tui.py          — Textual PeekApp (HEADER, ListView, filter, open, t/w/c)
  pack.py         — --pack (token budget, --ask, --format, --clip, --diff)
  find.py         — find (keyword + semantic)
  wtf.py          — wtf traceback explainer
  watch.py        — watch_repo polling + watchfiles
  mcp_server.py   — MCP stdio for Claude Code (peek mcp)
  llm.py          — LLM helpers
  cli.py          — Typer entry
  config.py       — config
  themes.py       — 10 themes
  tools/          — gen_demo.py
  tests/          — pytest
```

## Guidelines

- Zero-config default. Flags for power users.
- Offline-first. No network in the happy path.
- Rich for static, Textual for TUI.
- Tests for every new feature.
- Keep the CLI surface small.

## Who We Welcome (and What We Don’t)

**We love beginners who want to learn!** :wave: :sparkles:

If you’re new to open source, picking a `good first issue`, reading the code, trying, asking questions in the issue or [Q&A Discussions](https://github.com/hariomlohardev/peek/discussions/categories/q-a), and learning as you go — **you are exactly who we built this for**. We’ll review with extra care, explain the “why” behind suggestions, and celebrate your first PR. You don’t need to be an expert — you just need to be curious and willing to understand the change you submit. :pray: :hugs:

**What we don’t allow is spam.** :no_entry:

- Copy-pasting an AI answer (Claude, ChatGPT, Copilot, etc.) without understanding it, without testing `pytest -q` + `ruff check`, and without being able to explain the `What/Why/How` in your own words.
- Mass-filing low-effort AI-generated PRs just to collect `good first issue` counts.

A PR — human or AI-assisted — must:

- [ ] **Pass tests** (`pytest -q` green) and `ruff check` clean
- [ ] **Follow the PR template** (`What/Why/How/Tests/Screenshots/Checklist`)
- [ ] **Be explainable** — you can answer “why did you choose this regex / why this file?” in review
- [ ] **Be one focused change** (one file, one issue, ~30 min as the issue says)

If a PR is clearly low-effort AI spam (fails tests, doesn’t match the issue’s `### Files` + `### Acceptance`, or the author can’t explain it), we’ll **close it with a kind note and a link back to this section**, and ask you to try again the human way. Repeated spam may lead to a temporary ban — not because we don’t like AI, but because we want every `good first issue` to stay a real learning opportunity for the next beginner. :recycle:

**Using AI as a helper is fine** — like a spell-checker — as long as *you* are the author who understands, tests, and owns the change. If you used AI, just say so in the PR (“Used Copilot for the regex, then tested with `pytest -k go -v`”), and be ready to discuss it.

Thanks for keeping `peek` a place where beginners can actually learn! :heart: :rocket:

## Reporting Issues

- Use GitHub Issues: https://github.com/hariomlohardev/peek/issues
- Include: `peek --version`, `peek scan --json` snippet, OS, terminal size

## Code of Conduct

Be kind. Be direct. Help the next person understand the codebase faster — that's the whole point of `peek`.

---

Built by [Hariom Lohar](https://hariomlohardev.github.io/) — hariomlohar.new@gmail.com
