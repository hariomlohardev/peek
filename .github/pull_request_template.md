# Pull Request Template

## What

<!-- What does this PR do? Link the relevant issue: Closes #123 -->

## Why

<!-- Why is this needed? What user pain does it solve? -->

## How

<!-- How did you implement it? Key files, approach -->

## Tests

Run these from the package directory (`cd peek` from the Git root):

- [ ] `python -m pytest -q` passes
- [ ] `ruff check peek` is clean
- [ ] `ruff format --check peek` is clean
- [ ] New test added for this change (if applicable)

<!-- Paste the real results. If you could not run a check, say so instead of ticking the box. -->
<!-- Documentation-only change? Say so and describe the manual checks you did (e.g. previewed the Markdown, compared commands with `peek/pyproject.toml` and `.github/workflows/ci.yml`). -->

## Screenshots (if you touched `peek --no-tui`, TUI, or themes)

<!-- Drop a screenshot or `peek --no-tui` output. Every output is a screenshot! -->

## Checklist

- [ ] Title is `feat:`, `fix:`, `docs:`, `test:`, or `chore:` (conventional)
- [ ] Commit messages are clean (no `Co-Authored-By`)
- [ ] Branch is `fix/thing` or `feat/thing` from `main`
- [ ] The relevant issue is linked (e.g. `Closes #123`)
- [ ] I understand this PR and can explain the What/Why/How in my own words — AI as a helper is okay, but I own this change (see `peek/CONTRIBUTING.md` “Who We Welcome”)

Thanks for contributing! :tada: :heart:

> **New here?** Pick a `good first issue` — https://github.com/hariomlohardev/peek/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22
