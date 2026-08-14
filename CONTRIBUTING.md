# Contributing to peek

Thanks for wanting to contribute! :tada: `peek` is small, fast, and zero-config — we keep the bar high for simplicity, but low for newcomers.

> **New here?** Start with a **Good First Issue** — 20 issues, each ~30 min, one file, copy-paste steps:
>
> [![Good First Issues](https://img.shields.io/github/issues/hariomlohardev/peek/good%20first%20issue?label=good%20first%20issues&color=7057ff)](https://github.com/hariomlohardev/peek/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
>
> **Browse:** https://github.com/hariomlohardev/peek/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22

See **[`peek/CONTRIBUTING.md`](peek/CONTRIBUTING.md)** for the full guide (Quick Start, How to Contribute, Project Structure, Guidelines).

**Quick Start (from repo root):**
```bash
git clone https://github.com/hariomlohardev/peek && cd peek
pip install -e "peek[dev]"
pytest -q          # 146 passed, 1 skipped
peek --no-tui && peek  # static + TUI (peek . also works)
riff check peek    # lint
```

**Workflow:**
1. Fork → `git checkout -b fix/thing`
2. Pick a `good first issue` (or any `help wanted`)
3. Code + test (one file, ~200 LOC, handle edge cases)
4. `pytest -q && ruff check` must pass
5. PR with `Closes #123` — we’ll review in 48h, `good first issue` PRs get priority :rocket:

**Need help?** Ask in [Q&A Discussions](https://github.com/hariomlohardev/peek/discussions/categories/q-a) or the issue itself — no question too small! :pray:

Built by [Hariom Lohar](https://hariomlohardev.github.io/) — `peek` is for everyone. :heart:
