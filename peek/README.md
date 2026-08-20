<p align="center">
  <img src="assets/demo.gif" width="800" alt="peek demo — htop for codebases (code-generated, 800x450, ~15s)" />
</p>
<p align="center"><em>Demo by code — <code>python -m peek.tools.gen_demo</code> • also <code>assets/demo.svg</code> + <code>assets/demo.html</code></em></p>

<h1 align="center">peek — htop for codebases</h1>

<p align="center"><strong>Understand any codebase in 5 seconds.</strong> <code>pip install peek-code && peek .</code></p>

<p align="center">
  <a href="https://pypi.org/project/peek-code/"><img src="https://img.shields.io/pypi/v/peek-code?label=pypi" alt="PyPI"/></a>
  <a href="https://pypi.org/project/peek-code/"><img src="https://img.shields.io/pypi/pyversions/peek-code" alt="Python"/></a>
  <img src="https://img.shields.io/badge/tests-146%20passed-brightgreen" alt="tests"/>
  <img src="https://img.shields.io/badge/themes-10-blueviolet" alt="themes"/>
  <img src="https://img.shields.io/badge/made%20with-Rich%20%2B%20Textual-ff7ed8" alt="Rich+Textual"/>
  <a href="https://github.com/hariomlohardev/peek/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22"><img src="https://img.shields.io/github/issues/hariomlohardev/peek/good%20first%20issue?label=good%20first%20issues&color=7057ff" alt="Good First Issues"/></a>
</p>

<p align="center"><em>5 seconds → polyglot graph, languages, stack, Start Here. Every output is a screenshot.</em></p>

---

## Install

```bash
pip install peek-code
# or
pipx install peek-code
uv tool install peek-code

# dev (with tests + demo generator) — from repo root:
pip install -e "./peek[dev]"
# or from peek/: pip install -e ".[dev]"
pipx install peek-code          # or: uv tool install peek-code
pip install -e ".[dev]" # dev — from peek/ (package dir)
```
Requires Python 3.11+. Deps: `typer`, `rich`, `textual`, `pathspec`.

> Full install → [`docs.md`](../docs.md#install)

## Quick Start

```bash
peek                      # TUI — q quit, / filter, j/k nav, o open, t cycle, w watch
peek --no-tui             # static Rich (CI / screenshot)
peek --theme dracula --html -o map.html && open map.html
peek graph --format svg -o graph.svg  # polyglot import graph → DOT/SVG/HTML
peek find "auth token" --semantic     # semantic BM25 (+ fastembed) — multi-word = intent
peek mcp                  # MCP server for Claude Code / any MCP client
```
Keys: `q` quit • `j/k` nav • `o` open `$EDITOR` • `/` filter • `enter` details • `esc` clear • `?` help • `t` theme • `w` watch

```bash
peek wtf                  # paste traceback → explain with Start Here hint
peek watch .              # live rescan on file change (polling, Ctrl+C)
peek config set theme dracula  # persists
```

> Full CLI → [`docs.md#cli-reference`](../docs.md#cli-reference) · TUI → [`docs.md#tui-guide`](../docs.md#tui-guide) · Semantic → [`docs.md#semantic`](../docs.md#semantic)

## Demo (by code)

```bash
python -m peek.tools.gen_demo        # → peek/assets/demo.gif (800×450, <3MB) + demo.svg
peek --html -o peek/assets/demo.html
pytest peek/tests/test_demo_assets.py -v
```

> How it works → [`docs.md#demo-video`](../docs.md#demo-video)

## Features

| What you get | Where |
|---|---|
| `.gitignore`-aware walk, languages/LOC, tech stack, entry points, polyglot graph (Python + JavaScript/TypeScript), PageRank | `peek scan` / `peek analyze` / `peek` (TUI) |
| TUI 10 themes, filter, open, HTML export, token-aware pack, ranked find (keyword + semantic) | `peek` / `--html` / `--pack` / `find` |
| `graph` DOT/SVG/HTML, `symbols` index (AST + JS regex), `semantic` BM25/fastembed, `index` cache | `peek graph --format svg` / `peek find "auth token" --semantic` |
| `pack` 3.0: tiktoken, `--clip`, `--dry-run`, `--diff`/`--staged`, URL `https://` | `peek --pack --clip --dry-run --diff HEAD` |
| `wtf`/`watch`/`config`/`mcp` server, never crashes, <1s for 500 files, offline | `peek wtf` / `peek watch .` / `peek mcp` |

> Full table → [`docs.md#features`](../docs.md#features)

## 10 Themes

```bash
peek --theme dracula
peek --theme-list  # anthropic-pro (default), cinematic, dracula, nord, catppuccin-mocha, tokyo-night, solarized-dark, github-dark, monokai, minimal-mono
```

Warm clay `anthropic-pro` → neon `cinematic` → `dracula` → `nord`. 15 tokens `#RRGGBB`, precedence `cli > PEEK_THEME > config > anthropic-pro`.

> Full table + previews → [`docs.md#10-themes`](../docs.md#10-themes)

## Documentation

- **Full manual:** [`docs.md`](../docs.md) — Install, Demo, Features, Themes, CLI, TUI, Symbols, Semantic, Graph, Git, MCP, WTF, Watch, Config

## v3 Highlights

- `polyglot` graph — Python AST + JavaScript/TypeScript `import`/`require` regex, `peek graph --format svg`
- `semantic` BM25 (`peek/embeddings.py`) + `fastembed`, `peek find "auth token" --semantic`, `peek --pack --ask "auth token" --semantic`
- `pack 3.0` — `--clip`/`--dry-run`/`--diff HEAD`/`--staged`, URL fetch, tiktoken; `peek mcp` stdio server for Claude Code

## v2 Highlights

- `peek wtf` / `peek pack v2 --format xml --budget 4000` / `peek config set theme dracula` / `peek watch .` (`w` toggle) / `t` theme cycle

## Development

```bash
git clone https://github.com/hariomlohardev/peek && cd peek
pip install -e ".[dev]"
pytest -q          # 146 passed, 1 skipped
peek --no-tui && peek  # static + TUI
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md). `ruff` + `pytest` before PR. Branch `v3`.

## Contributing — Good First Issues

New to open source? Start here — **20 `good first issue`s, each ~30 min, one file, copy-paste steps:**

<a href="https://github.com/hariomlohardev/peek/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22"><img src="https://img.shields.io/github/issues/hariomlohardev/peek/good%20first%20issue?label=good%20first%20issues&color=7057ff" alt="Good First Issues"/></a>

**Browse:** https://github.com/hariomlohardev/peek/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22

- **Beginner (30 min):** docstrings, typo fixes, `--help` examples, `peek --version` test — pick any, no setup beyond `pip install -e ".[dev]"`
- **Intermediate (60-90 min):** `tiktoken` tokens, `peek diff`, `peek serve`, symbol index
- **Complex (1-2 days):** `peek-mcp` for Claude Code, polyglot `tree-sitter`, semantic embeddings, `peek-vscode`

Every issue has **exact file**, **acceptance checkboxes**, and `pytest -q` gate. PRs with `good first issue` label get priority review.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for `ruff` + `pytest` workflow. Branch `v3` is the big upshift (polyglot + semantic + MCP).

## Why peek?

Every output is a screenshot. Every repo is a new demo. `pip install peek-code` is zero friction — unlike `gitingest` (no ranking) or `pydeps` (no TUI).

## License

MIT — [`LICENSE`](LICENSE) · Built by [Hariom Lohar](https://hariomlohardev.github.io/) — hariomlohar.new@gmail.com
