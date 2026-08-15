# LinkedIn — Short Post (copy-paste)

Where do you start in a new repo? `tree` shows 200 files. `tokei` counts 13k LOC. Neither tells you that `cli.py` is the front door and `scanner.py` (imported by 12) is the hub.

I built `peek` — `pip install peek-code && peek .` → 5 seconds to see languages, stack, **Start Here ranked**, and import graph. 146 tests, offline, no API key.

The core is `analyzer.py` — 700 lines, no `networkx`. Files are web pages, imports are links:

```python
score = pr_norm*5 + in_norm*1.2 + entry_bonus 5.0 + guard_bonus 0.5 + depth 0.3 - __init__ 3.0 - <10 LOC 1.5
# PageRank 5 iter (damping 0.85) + in-degree + if __name__ == "__main__": via AST
```

On its own codebase: `cli.py 11.7` beats `scanner.py 7.5` — feels obvious, math is boring, result is magic.

Try it:
```bash
pip install peek-code && peek .
peek graph --format svg -o graph.svg
peek find "validate_token" .
```

Full walkthrough: https://github.com/hariomlohardev/peek/blob/main/docs/internals-pagerank.md
20 good first issues (30 min, one file): https://github.com/hariomlohardev/peek/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22

Built by Hariom Lohar — `peek` is the `htop` for codebases. A ⭐ helps more than you think.

#Python #OpenSource #ShowDev

---
Media: `peek/assets/demo.gif` (first image) + hub diagram `cli.py → scanner.py → analyzer.py`
Post Tue-Thu 08:00 UTC, first comment: “Code in `peek/peek/analyzer.py` lines 366–525 — happy to answer Qs!”
Also building Inkdown for Windows — feedback welcome: https://github.com/hariomlohardev/inkdown/releases/tag/WINDOWS
