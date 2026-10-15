# Contributing to peek

Thanks for wanting to contribute! :tada: `peek` is small, fast, and zero-config — we keep the bar high for simplicity, but low for newcomers.

> **New here?** Start with a **Good First Issue** — browse the open ones, each with clear steps:
>
> [![Good First Issues](https://img.shields.io/github/issues/hariomlohardev/peek/good%20first%20issue?label=good%20first%20issues&color=7057ff)](https://github.com/hariomlohardev/peek/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
>
> **Browse:** https://github.com/hariomlohardev/peek/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22

See **[`peek/CONTRIBUTING.md`](peek/CONTRIBUTING.md)** for the full guide (Quick Start, How to Contribute, Project Structure, Guidelines).

**Quick Start (from repo root):**

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

Then install and run checks from the Git root (package lives in `peek/`):

```bash
git clone https://github.com/YOUR-USERNAME/peek && cd peek
python -m pip install -e "./peek[dev]"
cd peek
python -m pytest -q
ruff check peek
# demo generator (optional): python -m peek.tools.gen_demo
```

Fork the repository, clone *your* fork, create a branch (`git checkout -b fix/thing`), and open a PR against the upstream `main`.

**Workflow:**
1. Fork → `git checkout -b fix/thing`
2. Pick a `good first issue` (or any `help wanted`)
3. Code + test (one file, ~200 LOC, handle edge cases)
4. `pytest -q && ruff check` must pass
5. PR with `Closes #123` — we’ll review in 48h, `good first issue` PRs get priority :rocket:

**Who we welcome:** Beginners who want to learn are *exactly* who we built `good first issue` for — we’ll review with extra care and explain the why. What we don’t allow is spam: copy-pasting AI without understanding, without `pytest -q`, and without being able to explain `What/Why/How` in your own words. PRs must be explainable and pass tests; AI as a helper (like spell-check) is fine as long as *you* own the change. See [`peek/CONTRIBUTING.md`](peek/CONTRIBUTING.md) for the full policy.

**Need help?** Ask in [Q&A Discussions](https://github.com/hariomlohardev/peek/discussions/categories/q-a) or the issue itself — no question too small! :pray:

Built by [Hariom Lohar](https://hariomlohardev.github.io/) — `peek` is for everyone. :heart:
