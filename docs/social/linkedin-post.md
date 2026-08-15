# LinkedIn — Internals Post: How I Built a PageRank-Style Ranker for Codebases

> **Copy-paste ready for LinkedIn. Add `peek/assets/demo.gif` as the first image and the hub diagram as the second. Keep line breaks — LinkedIn collapses after 3 lines, so the hook is critical.**

---

**Post:**

Where do you start in a new codebase? Every `git clone` asks it, and `tree` + `tokei` never answer.

I built `peek` — `pip install peek-code && peek .` → 5 seconds to see languages, stack, **Start Here ranked**, and import graph. No API key, 146 tests, offline.

The core is `analyzer.py` — 700 lines you can read in one sitting. Here’s how the ranking actually works:

**1. Files are web pages, imports are links.**

`scanner.py` is imported by 12 modules. `analyzer.py` is imported by `cli.py` which is itself central → double boost. But unlike the web, code has *intent*: `cli.py`, `main.py`, `__main__.py`, or `if __name__ == "__main__":` should float to the top even if nothing imports it.

So the score is **centrality + intent**.

**2. The hard part isn’t PageRank — it’s `import` parsing.**

- `src/` layout: `src/peek/scanner.py` must match `from peek.scanner import Foo` → strip `src/` prefix, longest-prefix + suffix fallback.
- Relative imports: `from . import foo` needs the file’s logical package (`_relative_base("peek.sub", 2)` → `"peek"`).
- BOM, `SyntaxError`, 500 KB files → swallow, never crash. `peek` never crashes is a feature.

All with `ast` — no regex for Python.

**3. The exact formula:**

```python
score = pr_norm*5        # PageRank 5 iter, damping 0.85 + dangling/N
      + in_norm*1.2      # in-degree, min(in_deg*1.2, 5.0)
      + entry_bonus 5.0  # cli.py/main.py/__main__.py/pyproject.scripts
      + guard_bonus 0.5  # if __name__ == "__main__": via AST (not substring!)
      + depth 0.3        # shallow files slightly preferred
      - __init__ 3.0     # package init is never Start Here
      - <10 LOC 1.5      # stubs
```

PageRank-lite is 5 iterations, `dangling_sum / N` spread — the 1998 paper on 29 nodes, not 30M.

One-line bug I shipped: `if '"__main__"' in text: return True` gave every file mentioning `__main__` in a comment +0.5. Fixed to AST walk for `Compare(left=Name(id="__name__"), comparators=[Constant(value="__main__")])`.

**4. On its own codebase:**

`peek --no-tui` → 210 files 13k LOC 0.35s
```
Start Here ⭐  cli.py 11.7 (entry, main guard, hub x7)
             scanner.py 7.5 (hub x12)
             themes.py 7.0 (hub x7)
```
`cli.py` wins because it has *all three*: central + hub 7 + entry + guard.

**5. Where it still breaks — and where you come in:**

I left seams on purpose, each is a `good first issue` with one file and a failing test:

- `len // 4` tokens → `tiktoken` `cl100k_base`
- `find` keyword-only → BM25 (`peek/peek/embeddings.py` already has it, just wire `find.py`)
- File-level graph → symbol-level (`peek/peek/symbols.py` + `tree-sitter` for JS/TS)

All are `good first issue` + `help wanted`, 30 min, `pytest -q` gate.

**Try it:**
```bash
pip install peek-code && peek .
peek graph --format svg -o graph.svg
peek find "validate_token" .
peek --pack --ask "auth" --format xml --budget 4000 | wc -c
```

`analyzer.py` is MIT, 700 lines, no `networkx`, no ML. If you’ve ever wanted to hack on ranking, graph viz, or “where should an agent look first?” — this is the seam.

👉 **Deep-dive:** https://github.com/hariomlohardev/peek/blob/main/docs/internals-pagerank.md
👉 **20 good first issues:** https://github.com/hariomlohardev/peek/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22
👉 **Discussions:** What repo should I demo next? https://github.com/hariomlohardev/peek/discussions

Built by Hariom Lohar — `peek` is the `htop` for codebases. If you liked the rabbit hole, a ⭐ helps more than you think.

---

**Hashtags (add at bottom, 3 max):** `#Python #OpenSource #ShowDev #CodeQuality #DeveloperTools`

**Media:**
1. `peek/assets/demo.gif` (800×450) as first image — shows `peek .` TUI alive
2. Hub diagram: `cli.py → scanner.py → analyzer.py` with `scanner.py` highlighted (or `peek/assets/themes/anthropic-pro.svg`)

**Posting tips:**
- Post Tuesday–Thursday 08:00–10:00 UTC for max dev reach.
- In first comment, drop: “Full code walkthrough in repo: `peek/peek/analyzer.py` lines 366–525 — happy to answer questions!”
- Tag 2-3 relevant: `Rich`, `Textual` — but not more.
- After posting, cross-link in `peek` Discussions → Show and tell.

---

*Also building **Inkdown** — a beautiful markdown editor for Windows — try it and share feedback:* https://github.com/hariomlohardev/inkdown/releases/tag/WINDOWS
