# Twitter/X — Internals Thread: PageRank for Codebases

> **Copy-paste ready — 8 tweets, each <280 chars. Post as a thread (reply to previous). Attach `peek/assets/demo.gif` to Tweet 1 and the hub diagram to Tweet 4.**

---

**Tweet 1/8 — Hook**
```
Where do I start in this repo? — every dev, every `git clone`.

I built `peek` to answer it in 5 sec, no API key.

`pip install peek-code && peek .` → 5 seconds → languages, stack, Start Here ranked, import graph.

How the ranking works 🧵
```
**Media:** `peek/assets/demo.gif` (800×450, 777KB)

**Tweet 2/8 — The problem is ranking, not listing**
```
`tree` shows 200 files.
`tokei` counts 13k LOC.
Neither tells you that `cli.py` is the front door and `scanner.py` (imported by 12) is the hub.

`peek` treats files like web pages.
Imports = links.
```

**Tweet 3/8 — The graph is the hard part**
```
Building the graph looks easy until `src/` layout breaks you.

`src/peek/scanner.py` → `peek.scanner`
`from . import foo` → needs the file's package, not just the string

`peek` normalizes `src/` + resolves relative imports via `ast` + longest-prefix + suffix fallback.

Never crashes on BOM/SyntaxError — it just skips.
```

**Tweet 4/8 — The formula (the meat)**
```
The score — line for line from `analyzer.py`:

score = pr_norm*5        # PageRank 5 iter, damping 0.85
      + in_norm*1.2      # in-degree
      + entry_bonus 5.0  # cli.py/main.py/__main__
      + guard_bonus 0.5  # if __name__ == "__main__": (via AST!)
      + depth 0.3
      - __init__ 3.0     # never Start Here
      - <10 LOC 1.5

On `peek` itself: cli.py 11.7 beats scanner.py 7.5
```

**Media:** Hub diagram — `cli.py → scanner.py → analyzer.py` with `scanner.py` highlighted as hub (or `peek/assets/themes/anthropic-pro.svg` as placeholder)

**Tweet 5/8 — One-line bug**
```
Early `_has_main_guard` was:

if '"__main__"' in text: return True

Every file mentioning `__main__` in a comment got +0.5.

Fix: walk the AST, only real

if __name__ == "__main__":
```

**Tweet 6/8 — Where it still breaks (your on-ramp)**
```
The seams I left on purpose — each is a good first issue:

• `len//4` tokens → `tiktoken`
• `find` keyword-only → BM25
• File-level graph → symbol-level

One file, 30 min, `pytest -q` gate.
```

**Tweet 7/8 — Try it**
```
pip install peek-code && peek .
# TUI: q quit, / filter, t cycle 10 themes, w watch

peek . --no-tui --theme dracula
peek graph --format svg -o graph.svg
peek find "validate_token" .
peek --pack --ask "auth" --format xml --budget 4000 | wc -c
```

**Tweet 8/8 — CTA**
```
`analyzer.py` is 700 lines you can read in one sitting. No networkx, no ML.

20 good first issues → https://github.com/hariomlohardev/peek/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22

Internals deep-dive: https://github.com/hariomlohardev/peek/blob/main/docs/internals-pagerank.md

⭐ if you liked the rabbit hole — it helps more than you think
```

**Hashtags for last tweet (optional, 1-2 max):** `#python` `#opensource` `#showdev`

---

**Posting tips:**
- Post Tweet 1, then reply to it 7 times quickly (so the thread stays together).
- Pin the thread for 7 days.
- Tag @willmcgugan (Rich/Textual) in Tweet 1 — he boosts Textual apps.
- After posting, drop the link in `peek` Discussions → Show and tell: https://github.com/hariomlohardev/peek/discussions/70
