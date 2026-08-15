# Contributing to peek

Thanks for wanting to contribute! `peek` is a small, fast, zero-config codebase — we keep the bar high for simplicity.

> **New here?** Start with a **Good First Issue** — 20 issues, each ~30 min, one file, copy-paste steps. They rank high on GitHub search and get priority review:
>
> <a href="https://github.com/hariomlohardev/peek/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22"><img src="https://img.shields.io/github/issues/hariomlohardev/peek/good%20first%20issue?label=good%20first%20issues&color=7057ff" alt="Good First Issues"/></a>
>
> **Browse:** https://github.com/hariomlohardev/peek/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22
>
> - **20 Good First Issue (30 min):** docstrings, `peek wtf --help` example, `peek --version` test — perfect for first PR
> - **10 Intermediate (60-90 min):** `tiktoken`, `peek diff`, `peek serve`
> - **5 Complex (1-2 days):** `peek-mcp`, polyglot, `peek-vscode`

## Quick Start

```bash
git clone https://github.com/hariomlohardev/peek && cd peek
pip install -e ".[dev]"
pytest -q
peek --no-tui   # static
peek            # TUI (q to quit)
```

## How to Contribute

1. **Fork** and create a branch: `git checkout -b fix/thing` or `feat/thing`
2. **Code**: keep it under ~200 LOC per file, handle edge cases (binary, huge, SyntaxError, empty, non-python)
3. **Test**: add a test in `tests/` — fixtures in temp dirs, no network, no `git clone` in tests
4. **Style**: `ruff check .` (line length 100), `pytest -q` must pass
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
  llm.py          — optional LLM summary
  config.py       — themes + .peek.toml (peek config)
  themes.py       — 10 themes (15 tokens)
  cli.py          — Typer app (scan, analyze, find, graph, watch, wtf, config, mcp, index, diff, hot)
  tools/gen_demo.py — Pillow demo GIF (800×450)
peek/tests/
  test_scanner.py, test_analyzer.py, test_renderer_pack_find.py, test_themes.py,
  test_comprehensive_tdd.py, test_demo_assets.py, test_cli_dot.py,
  test_symbols.py, test_embeddings.py, test_graph.py, test_pack_v3.py,
  test_mcp.py, test_git.py, test_tui_live.py, test_watch.py, test_wtf.py
.github/
  workflows/ci.yml, release.yml — CI + PyPI publish
  ISSUE_TEMPLATE/ — bug_report, feature_request, good_first_issue
  pull_request_template.md
  CODEOWNERS
```

## Workflows & Automation

- **CI** (`.github/workflows/ci.yml`): runs on `push`/`PR` to `main`/`v3` — `ruff check`, `pytest -q` (3× Python 3.11-3.13, Ubuntu + Windows), `twine check`, demo asset check. Must be green to merge.
- **Release** (`.github/workflows/release.yml`): on `git tag v*` — builds `peek/dist` and publishes to PyPI + GitHub Release (via `pypa/gh-action-pypi-publish`).
- **Issue templates:** `bug_report`, `feature_request`, `good_first_issue` (with `good first issue` + `help wanted` labels) — use them so issues rank.
- **PR template:** `.github/pull_request_template.md` — fill What/Why/How/Tests/Screenshots.

## Good First Issue Workflow (for maintainers)

1. Label `good first issue` + `help wanted` → appears in https://github.com/search?q=label%3A%22good+first+issue%22+language%3Apython
2. Keep to **one file, 30 min, copy-paste steps**, with `### Files` + `### Acceptance` checkboxes.
3. PRs with `good first issue` get priority review (48h) and are featured in release notes.

## Guidelines

- **Never crash** — every `scan`/`analyze` must handle weird files gracefully
- **Zero config** — works on any path, Python or not, offline, no API key required
- **Fast** — <2 sec for 500 files, cap at 2000 for MVP
- **Beautiful** — every `peek --no-tui` output should be screenshot-ready (test in 80x24 and 120x40)
- **No push in PRs** — don't `git push` to upstream; fork it

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
