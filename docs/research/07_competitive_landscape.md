# Competitive Landscape — `peek` Moat & Positioning

> Where `peek` sits, who could kill it, and why they won't in the 5-day window.

---

## 1. Direct Competitors — Feature Matrix

| Tool | What it does | Stars | `peek` advantage |
|---|---|---|---|
| **gitingest** | Repo → LLM prompt (URL → text dump) | ~8k | `peek` ranks + visualizes; gitingest is dumb dump, no map |
| **repomix** | Repo → packed XML for LLMs | ~12k | Same — `peek` is smart map, repomix is packer; `peek --pack` will match it |
| **Sourcegraph** | Code search + intelligence (enterprise) | — | Heavy, cloud, $$, not local CLI; `peek` is `pip install` |
| **pydeps** | Python dependency graph (DOT) | ~500 | Ugly DOT output, not interactive, not ranked, no summary |
| **import-linter** | Enforce import rules | ~300 | Linter, not explorer — different job |
| **tree / exa / eza** | File tree | — | No semantics, no ranking, no graph |
| **pygount / tokei** | LOC counting | — | Single metric, not overview |
| **pipdeptree** | Pip dependency tree | ~300 | Text-only, pip deps only, not import graph |
| **code2flow** | Code → flowchart | ~1k | Flowchart per file, not repo map |
| **GitHub file browser** | Flat file list | — | No relationships, no ranking |

### The gap visualized

```
                    Beautiful
                       ↑
                       │
              peek ●───┼───● rich/textual (not codebase-specific)
                       │
  Smart ◄──────────────┼──────────────► Dumb
  (ranked,            │            (flat dump)
   semantic)          │
                       │
              gitingest●
              repomix  ●───● tree / find / grep
                       │
                       ↓
                     Ugly
```

**`peek` is alone in the top-right: smart + beautiful.** That's the moat.

---

## 2. Indirect Competitors — "Good Enough" Alternatives

| Alternative | When people use it | Why they still want `peek` |
|---|---|---|
| README + `find`/`grep` | Default for most devs | 30 min vs 5 sec; no ranking |
| IDE (VS Code, PyCharm) "go to def" | Daily | Requires IDE setup; no overview map |
| Asking a teammate "where is X?" | Onboarding | Not always possible; doesn't scale |
| Claude/Cursor "explain this repo" | AI users | Hits token limits; no visual map; slow |
| `tree` + `wc -l` | Quick peek | No intelligence |

**`peek` doesn't need to be 10× better than these — it needs to be 10× *faster* and more *beautiful*. It is.**

---

## 3. Why `peek` Won't Be Killed Quickly

### "What if someone clones it in Rust and makes it 10× faster?"

- **Speed is not `peek`'s moat.** Scanning 500 files in 0.2s (Rust) vs 1.5s (Python) doesn't change the user outcome — both feel instant. The value is *ranking + beauty + summary*, not raw scan speed.
- **Python is the right language** — audience is Python devs, analysis is Python AST, ecosystem is Python (pip install). A Rust clone would alienate the core audience.
- **Historical precedent:** `rich` (Python) has 48k stars despite Rust alternatives — beauty + ergonomics beat raw speed for DX tools.

### "What if gitingest/repomix adds a map?"

- They could, but their positioning is "packer" not "understander." Adding a map would be a pivot, not a feature.
- `peek`'s map + ranking + TUI is a full product, not a button. First-mover with polish wins the category (like `htop` vs `top`).

### "What if GitHub adds this natively?"

- GitHub has had years to add codebase maps and hasn't — their file browser is still flat. Enterprise priorities ≠ indie dev UX.
- Even if they do, `peek` is local, offline, works on any repo (including private/local), and is pip-installable — GitHub can't replace that.

### "What if an AI does this automatically?"

- AI *could* summarize a repo, but it needs context (which files matter?) — that's exactly what `peek` provides. `peek` *feeds* AI, it doesn't compete with it.
- `peek --pack` is the bridge: ranked files → LLM context. AI makes `peek` more valuable, not less.

---

## 4. Positioning — How to Talk About `peek`

### One-liners (pick one per channel)

| Channel | One-liner |
|---|---|
| **HN title** | "Show HN: peek — htop for codebases (understand any repo in 5 seconds)" |
| **Twitter** | "I got tired of spending 30 min understanding a new repo. So I built peek — `pip install peek && peek .` and you get a beautiful map of what it does, where to start, and what talks to what." |
| **Reddit r/Python** | "peek: a Python-native codebase cartographer — `peek .` gives you architecture, entry points, and 'start here' in 5 sec (Rich + Textual, zero config)" |
| **PyPI description** | "The htop for codebases — understand any repo in 5 seconds." |
| **Elevator (verbal)** | "You know htop? peek is htop for code. Run it in any repo and instantly see what it does and where to start." |

### Comparison table (for README)

```markdown
| Feature | peek | gitingest | tree | Sourcegraph |
|---|---|---|---|---|
| One-liner install | ✅ `pip install peek` | ✅ | ✅ | ❌ (enterprise) |
| Zero config | ✅ | ✅ | ✅ | ❌ |
| Beautiful output | ✅ Rich+Textual | ❌ | ❌ | ⚠️ web only |
| Ranked "start here" | ✅ | ❌ | ❌ | ❌ |
| Architecture map | ✅ | ❌ | ❌ | ⚠️ |
| Works offline | ✅ | ✅ | ✅ | ❌ |
| Interactive TUI | ✅ | ❌ | ❌ | ❌ |
| LLM pack (ranked) | ✅ `--pack` | ✅ (unranked) | ❌ | ❌ |
```

### What `peek` is NOT (to avoid mispositioning)

- Not a linter, formatter, or tester — no style opinions
- Not an IDE — no editing, just understanding
- Not a replacement for `gitingest` if you want *every* file dumped — `peek` is curated, `gitingest` is exhaustive
- Not enterprise — it's for the individual dev, the side-project explorer, the new hire

---

## 5. Moat — What Makes `peek` Defensible Beyond Day 5

| Moat | How it builds over time |
|---|---|
| **Category ownership** | First "htop for codebases" with polish owns the mental slot (like `htop` owns system viz) |
| **Platform, not tool** | Every new feature (`--pack`, `--find`, `--explain`) adds a viral surface and a search keyword |
| **Community maps** | Users sharing `peek` outputs for famous repos creates UGC flywheel |
| **Textual showcase** | `peek` becomes the flagship Textual app — Textual team promotes it, driving stars |
| **PyPI + GitHub SEO** | `peek`, `codepeek`, `codebase map` keywords compound over months |

**The real moat is not code — it's the README GIF that everyone has seen.** Once 5k devs have seen the `peek` demo, the next tool needs to be 10× better to displace it. That's the window to build v0.2.0.

---

## 6. If You Want to Hedge — Two-Repo Strategy

If you're worried about `peek` not landing, hedge with a **companion micro-tool** that shares 80% of the code:

| Repo | Scope | Effort | Viral angle |
|---|---|---|---|
| **`peek`** (main) | Full codebase map | 5 days | Universal, visual, platform |
| **`wtf`** (micro, optional day 6–7) | `wtf python app.py` — beautiful traceback explainer | 1–2 days (reuses Rich, scanner) | Side-by-side GIF, funny name, huge TAM |

Ship `peek` first. If it gets 500+ stars week 1, `wtf` can be `peek --explain` in v0.2.0. If `peek` stalls, `wtf` is a second launch with a different viral hook (humor + pain).

But **don't split focus during the 5 days** — `peek` alone is enough. Hedge is for week 2.

---

*Next → `08_launch_playbook.md` — hour-by-hour launch checklist.*


---
*Author: **Hariom Lohar** -- hariomlohar.new@gmail.com -- https://hariomlohardev.github.io/ -- 2026-08-10*

