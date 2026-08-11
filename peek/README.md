<p align="center">
  <img src="assets/demo.gif" width="800" alt="peek demo — htop for codebases (code-generated, 800x450, ~15s)" />
</p>
<p align="center"><em>Demo by code — <code>python -m peek.tools.gen_demo</code> • also <code>assets/demo.svg</code> + <code>assets/demo.html</code></em></p>

<h1 align="center">peek — htop for codebases</h1>

<p align="center"><strong>Understand any codebase in 5 seconds.</strong> <code>pip install peek-code && peek .</code></p>

<p align="center">
  <a href="https://pypi.org/project/peek-code/"><img src="https://img.shields.io/pypi/v/peek-code?label=pypi" alt="PyPI"/></a>
  <a href="https://pypi.org/project/peek-code/"><img src="https://img.shields.io/pypi/pyversions/peek-code" alt="Python"/></a>
  <img src="https://img.shields.io/badge/tests-108%20passed-brightgreen" alt="tests"/>
  <img src="https://img.shields.io/badge/themes-10-blueviolet" alt="themes"/>
  <img src="https://img.shields.io/badge/made%20with-Rich%20%2B%20Textual-ff7ed8" alt="Rich+Textual"/>
</p>

<p align="center"><em>5 seconds → languages, stack, Start Here, graph. Every output is a screenshot.</em></p>

---

## Install

```bash
pip install peek-code
pipx install peek-code          # or: uv tool install peek-code
pip install -e "peek[dev]" # dev — pyproject is at peek/pyproject.toml
```
Requires Python 3.11+. Deps: `typer`, `rich`, `textual`, `pathspec`.

> Full install → [`docs.md`](../docs.md#install)

## Quick Start

```bash
peek                      # TUI — q quit, / filter, j/k nav, o open, t cycle, w watch
peek --no-tui             # static Rich (CI / screenshot)
peek --theme dracula --html -o map.html && open map.html
```
Keys: `q` quit • `j/k` nav • `o` open `$EDITOR` • `/` filter • `enter` details • `esc` clear • `?` help • `t` theme • `w` watch

```bash
peek wtf                  # paste traceback → explain with Start Here hint
cat tb.txt | peek wtf
peek watch .              # live rescan on file change (polling, Ctrl+C)
peek config set theme dracula  # persists
```

> Full CLI → [`docs.md#cli-reference`](../docs.md#cli-reference) · TUI → [`docs.md#tui-guide`](../docs.md#tui-guide) · WTF → [`docs.md#wtf`](../docs.md#wtf---traceback-explainer) · Watch → [`docs.md#watch`](../docs.md#watch---live-rescan) · Config → [`docs.md#config-set`](../docs.md#config-set)

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
| `.gitignore`-aware walk, languages/LOC, tech stack, entry points, import graph, PageRank ranking | `peek scan` / `peek analyze` / `peek` (TUI) |
| TUI with 10 themes, filter, open, HTML export, token-aware pack, ranked find, optional LLM | `peek` / `--html` / `--pack` / `find` / `--llm` |
| `wtf` traceback explainer (scan-aware Start Here hint), `watch` live rescan (polling 0.8s/debounce 0.4s, `w` toggle), `config set/get/list` persistent theme, `t` live theme cycling | `peek wtf` / `peek watch .` / `peek watch` + `w` / `peek config set theme dracula` / `t` |
| Never crashes, <1s for 500 files, offline, no API key | — |

> Full 5-col table + vs others → [`docs.md#features`](../docs.md#features)

## 10 Themes

```bash
peek --theme dracula
peek --theme-list  # anthropic-pro (default), cinematic, dracula, nord, catppuccin-mocha, tokyo-night, solarized-dark, github-dark, monokai, minimal-mono
```

Warm clay `anthropic-pro` → neon `cinematic` → `dracula` → `nord`. 15 tokens `#RRGGBB`, precedence `cli > PEEK_THEME > config > anthropic-pro`.

> Full table + previews → [`docs.md#10-themes`](../docs.md#10-themes)

## Documentation

- **Full manual:** [`docs.md`](../docs.md) — Install, Demo, Features, Themes, CLI, TUI, Pack/Find/LLM, WTF, Watch, Config Set, Architecture, Testing
- **Research:** [`docs/research/`](../docs/research/) — viral thesis, candidates, 5-day plan
- **Plans:** [`docs/superpowers/`](../docs/superpowers/)

## v2 Highlights

- `peek wtf` → traceback explainer, parses `Traceback` + `Error` + frames, Start Here hint — no LLM
- `peek pack --format xml --budget 4000 --include "*.py"` → token-smart pack v2 with budget and globs
- `peek config set theme dracula` → writes `~/.peek/config.toml`, `get/list` validated via `get_theme`
- `peek watch .` / `peek --watch` (`w` toggle) → polling 0.8s / debounce 0.4s, `watchfiles` if installed
- `t` → live cycle 10 themes in TUI

## Development

```bash
git clone https://github.com/hariomlohardev/peek && cd peek
pip install -e "peek[dev]"
pytest -q          # 108 passed, 1 skipped
peek --no-tui && peek  # static + TUI
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md). `ruff` + `pytest` before PR. Branch `v2`.

## Why peek?

Every output is a screenshot. Every repo is a new demo. `pip install peek-code` is zero friction — unlike `gitingest` (no ranking) or `pydeps` (no TUI).

## License

MIT — [`LICENSE`](LICENSE) · Built by [Hariom Lohar](https://hariomlohardev.github.io/) — hariomlohar.new@gmail.com
