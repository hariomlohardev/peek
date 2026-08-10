# Contributing to peek

Thanks for wanting to contribute! `peek` is a small, fast, zero-config codebase — we keep the bar high for simplicity.

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
  scanner.py    — walk + .gitignore + LOC + tech stack + entry
  analyzer.py   — AST graph + PageRank + ranking + summary
  renderer.py   — Rich static panels + build_html
  _ascii_graph.py — one-liner graph
  tui.py        — Textual PeekApp (HEADER, ListView, filter, open)
  pack.py       — --pack (token budget, --ask)
  find.py       — find (filename + content, ranked)
  llm.py        — optional LLM summary
  cli.py        — Typer app (scan, analyze, find, peek [PATH])
tests/
  test_scanner.py, test_analyzer.py, test_renderer_pack_find.py
```

## Guidelines

- **Never crash** — every `scan`/`analyze` must handle weird files gracefully
- **Zero config** — works on any path, Python or not, offline, no API key required
- **Fast** — <2 sec for 500 files, cap at 2000 for MVP
- **Beautiful** — every `peek --no-tui` output should be screenshot-ready (test in 80x24 and 120x40)
- **No push in PRs** — don't `git push` to upstream; fork it

## Reporting Issues

- Use GitHub Issues: https://github.com/hariomlohardev/peek/issues
- Include: `peek --version`, `peek scan --json` snippet, OS, terminal size

## Code of Conduct

Be kind. Be direct. Help the next person understand the codebase faster — that's the whole point of `peek`.

---

Built by [Hariom Lohar](https://hariomlohardev.github.io/) — hariomlohar.new@gmail.com
