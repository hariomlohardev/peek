# Contributing to peek

Thanks for wanting to contribute! :tada: `peek` is small, fast, and zero-config — we keep the bar high for simplicity, but low for newcomers.

> **New here?** Start with a **Good First Issue** — small, one-file changes with copy-paste steps:
>
> [![Good First Issues](https://img.shields.io/github/issues/hariomlohardev/peek/good%20first%20issue?label=good%20first%20issues&color=7057ff)](https://github.com/hariomlohardev/peek/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
>
> **Browse:** https://github.com/hariomlohardev/peek/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22

See **[`peek/CONTRIBUTING.md`](peek/CONTRIBUTING.md)** for the full guide (Quick Start, How to Contribute, Project Structure, Guidelines).

**Quick Start (from the Git root):**
```bash
# 1. Fork the repository on GitHub, then clone YOUR fork and create a branch
git clone https://github.com/<your-username>/peek && cd peek
git checkout -b fix/thing

# 2. Create a virtual environment (Python 3.11+)
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\Activate.ps1      # Windows PowerShell

# 3. Install from the Git root - the package manifest is peek/pyproject.toml
python -m pip install -e "./peek[dev]"

# 4. Tests, lint, and the demo generator run from peek/
cd peek
python -m pytest -q
ruff check peek
python -m peek.tools.gen_demo    # optional: regenerate the demo GIF
```

**Workflow:**
1. Fork → `git checkout -b fix/thing`
2. Pick a `good first issue` (or any `help wanted`)
3. Code + test (one file, ~200 LOC, handle edge cases)
4. `pytest -q && ruff check` must pass
5. PR with `Closes #123` — we’ll review in 48h, `good first issue` PRs get priority :rocket:

**Who we welcome:** Beginners who want to learn are *exactly* who we built `good first issue` for — we’ll review with extra care and explain the why. What we don’t allow is spam: copy-pasting AI without understanding, without `pytest -q`, and without being able to explain `What/Why/How` in your own words. PRs must be explainable and pass tests; AI as a helper (like spell-check) is fine as long as *you* own the change. See [`peek/CONTRIBUTING.md`](peek/CONTRIBUTING.md) for the full policy.

**Need help?** Ask in [Q&A Discussions](https://github.com/hariomlohardev/peek/discussions/categories/q-a) or the issue itself — no question too small! :pray:

Built by [Hariom Lohar](https://hariomlohardev.github.io/) — `peek` is for everyone. :heart:
