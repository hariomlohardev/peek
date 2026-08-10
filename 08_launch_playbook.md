# Launch Playbook — From `git push` to GitHub Trending

> **Goal:** 1k stars week 1, 5k month 1. This is a checklist, not a strategy doc — follow it hour by hour.
>
> **Precondition:** `peek` v0.1.0 is on PyPI, GitHub repo is polished, demo GIF is ready, README is launch-ready (see Day 5 in `06_five_day_build_plan.md`).

---

## 0. Pre-Launch Checklist (Day 5 Evening — Before You Sleep)

### Repo readiness

- [ ] `pip install peek` works in fresh venv on macOS + Linux (test on two machines or Docker)
- [ ] `peek .` and `peek . --no-tui` both beautiful at 80×24 and 120×40
- [ ] `demo.gif` < 3MB, < 20 sec, loops, no audio, 800px wide, visible without scrolling in README
- [ ] README: GIF at top, install + usage in first 200px, no scrolling needed to understand what it does
- [ ] `LICENSE` (MIT), `CONTRIBUTING.md` (minimal), `pyproject.toml` metadata complete
- [ ] GitHub repo: description = "The htop for codebases — understand any repo in 5 seconds", topics = `python`, `cli`, `tui`, `textual`, `rich`, `codebase`, `visualization`, `developer-tools`
- [ ] `git tag v0.1.0 && git push --tags` + GitHub Release with notes + GIF
- [ ] PyPI: `https://pypi.org/project/peek/` shows correct README, `pip install peek` badge, no warnings

### Content readiness (drafts, not yet published)

- [ ] HN post: title + body + first comment (see §1)
- [ ] Twitter thread: 3 tweets + GIF + GitHub link (see §2)
- [ ] Reddit r/Python post: title + body (see §3)
- [ ] Product Hunt draft (optional, day 2–3)
- [ ] Newsletter submissions: PyCoder's Weekly, TLDR, Console.dev (bookmarked, forms ready)

### Timing

- [ ] Launch is **Tue, Wed, or Thu** — not Mon/Fri/weekend
- [ ] HN post scheduled for **08:00–10:00 UTC** (max US+EU overlap)
- [ ] You have **2 hours free after posting** to reply to every comment (critical for HN ranking)

---

## 1. Hacker News — Show HN (Hour 0 — 08:00 UTC)

### Title

```
Show HN: peek — htop for codebases (understand any repo in 5 seconds)
```

**Why this title:**
- "Show HN:" — required for Show HN
- "htop for codebases" — metaphor, instantly understood
- "(understand any repo in 5 seconds)" — benefit + number

### Body (Show HN self-post)

```markdown
Hey HN — I got tired of spending 30 minutes understanding a new repo
every time I cloned one. README lies, `find`/`grep` are noisy, and
asking a teammate isn't always possible.

So I built peek — `pip install peek && peek .` and in 5 seconds you
get:

- What the repo does (heuristic summary, no API key needed)
- Where to start (ranked "start here" list)
- What talks to what (import graph)
- Tech stack + stats

It's Python-native (AST-based), beautiful (Rich + Textual), zero-config,
and works offline. `peek .` for TUI, `peek . --no-tui` for static
(screenshot-friendly), `peek --find "auth"` to search.

Demo GIF in the README. Works on any repo, but Python repos get the
richest maps.

Would love feedback — especially on ranking ("start here" accuracy)
and what you'd want from `peek --pack` (ranked LLM context packing).

GitHub: https://github.com/YOU/peek
PyPI: https://pypi.org/project/peek/
```

### First comment (post immediately after, as author)

```markdown
Thanks for checking it out! Some details:

- Built in 5 days, Python + Rich + Textual, ~1k lines
- Heuristics first (no LLM needed), optional LLM summary if you set
  OPENAI_API_KEY / ANTHROPIC_API_KEY
- Handles non-Python repos gracefully (file tree + tech stack, no AST)
- `peek . --html` exports a shareable HTML map

Happy to answer anything — and if you try `peek` on a famous repo,
I'd love to see the screenshot!
```

### HN tactics

- [ ] Post and **immediately upvote yourself** (you get one)
- [ ] Reply to **every comment within 15 min** for first 2 hours — HN algorithm rewards engagement
- [ ] Don't ask friends to upvote inorganically — HN detects and penalizes
- [ ] If post doesn't hit front page in 1 hour, don't repost same day — try again in 1 week with new angle
- [ ] Cross-link: after HN post is live, tweet "I just launched peek on HN — would love your upvote/feedback: <HN link>"

---

## 2. Twitter / X (Hour 0 + 30 min — 08:30 UTC)

### Tweet 1 (main, with GIF)

```
I got tired of spending 30 min understanding every new repo I cloned.

So I built peek — htop for codebases.

  pip install peek && peek .

5 seconds → beautiful map of what it does, where to start, what talks to what.

No API key. No config. Just `peek .` 🧵

[demo.gif]
[GitHub link]
```

### Tweet 2 (reply to Tweet 1 — the demo)

```
It works on any repo, but Python repos get the richest maps (AST import graph).

Here's peek on django, requests, and a tiny side project — every map is different, every map is useful.

[screenshots collage or 2nd GIF]
```

### Tweet 3 (reply to Tweet 2 — the CTA)

```
Open source (MIT), ~1k lines of Python, Rich + Textual.

  pip install peek
  peek .              # TUI
  peek . --no-tui     # static (for screenshots)
  peek --find "auth"  # search

GitHub: github.com/YOU/peek
PyPI: pypi.org/project/peek

Would love stars, feedback, and screenshots of peek on your favorite repos!
```

### Twitter tactics

- [ ] Pin Tweet 1 to profile for 1 week
- [ ] Tag 2–3 relevant people with genuine note (not spam):
  - `@willmcgugan` (Rich/Textual author — "built with Rich/Textual, thought you'd like it")
  - `@simonw` (datasette, loves Python CLI tools)
  - One AI-adjacent (e.g., `@karpathy` only if you have a legit angle — don't spam)
- [ ] Reply to every reply in first 2 hours
- [ ] Post same GIF as standalone to r/Python's Twitter-adjacent communities (Mastodon, Bluesky) if you use them
- [ ] Use hashtags sparingly: `#python` `#cli` `#opensource` (1–2 max, not 5)

---

## 3. Reddit (Hour 2 — 10:00 UTC)

### r/Python

**Title:**
```
peek — htop for codebases: understand any repo in 5 seconds (Python + Rich + Textual, pip install peek)
```

**Body:**
```markdown
Hey r/Python — I built [peek](https://github.com/YOU/peek), a Python-native codebase cartographer.

`pip install peek && peek .` in any repo and in 5 seconds you get:
- What it does (heuristic summary, no LLM needed)
- Ranked "start here" list (entry points + most-central files)
- Import graph + tech stack + stats
- Interactive TUI (Textual) + static mode + HTML export

It's ~1k lines, AST-based, zero-config, works offline. I built it because I was tired of `find`/`grep`/`README` every time I cloned something new.

Demo GIF in the README. Would love feedback, especially on ranking accuracy.

GitHub: https://github.com/YOU/peek
```

### r/programming (if r/Python goes well, 4 hours later)

Shorter, more general title: "peek — understand any codebase in 5 seconds"

### Reddit tactics

- [ ] Don't post to 5 subreddits at once — 1–2 max day 1, more day 2–3
- [ ] Reply to every comment
- [ ] Don't be defensive about criticism — "great point, added to roadmap" is the right answer
- [ ] If post gets removed (self-promo rule), message mods politely — most allow Show HN-style launches

---

## 4. Product Hunt (Day 2 — 09:00 UTC)

### Listing

- **Name:** peek — htop for codebases
- **Tagline:** Understand any codebase in 5 seconds
- **Description:** `pip install peek && peek .` — beautiful, instant architecture maps for any repo. Ranked "start here," import graph, tech stack. Python-native, Rich + Textual, zero config, works offline.
- **Gallery:** GIF + 2 screenshots + architecture diagram
- **Topics:** Developer Tools, Open Source, Python
- **Maker comment:** Same story as HN, shorter

### Tactics

- [ ] Submit Tue–Thu, not weekend
- [ ] Ask 3–5 friends to upvote + comment in first hour (Product Hunt is more lenient than HN)
- [ ] Engage with every Product Hunt comment

---

## 5. Newsletters (Day 2–3 — Submit, Wait)

| Newsletter | URL | Lead time | What to submit |
|---|---|---|---|
| **PyCoder's Weekly** | pycoders.com/submit | Weekly (Tue) | Link + 1-sentence pitch |
| **TLDR** | tldr.tech | Daily | Submit via form |
| **Console.dev** | console.dev | Weekly | "Developer tool of the week" |
| **Python Bytes** | pythonbytes.fm | Weekly | Email hosts |
| **Changelog** | changelog.com | Weekly | Submit via GitHub |

- [ ] Submit to all 5 on day 2, even if you only get 1 inclusion — that's 10k+ eyeballs

---

## 6. GitHub — Optimize for Trending (Ongoing)

### GitHub trending algorithm (observed)

- Trending is per-language, per-day. Python trending is very achievable (needs ~100–300 stars/day for top 10).
- Stars in first 24h matter most.
- Stars from diverse accounts > stars from one org.

### Checklist

- [ ] Repo has `python` topic + 7 other topics (max visibility)
- [ ] README has social preview image (Settings → Social preview → upload GIF frame)
- [ ] Pin `peek` to your GitHub profile
- [ ] Star history will be public — no fake stars, no star farms (GitHub detects)
- [ ] Add `FUNDING.yml` later (GitHub Sponsors) — not day 1, but week 2

---

## 7. Post-Launch — The First 48 Hours Are Everything

### Hour-by-hour after HN post

| Time | Action |
|---|---|
| 0–2h | Reply to every HN comment + Twitter reply within 15 min |
| 2–4h | Post to Reddit r/Python; cross-tweet HN link |
| 4–8h | Monitor GitHub stars/issues; fix any `pip install` breakage IMMEDIATELY |
| 8–12h | If HN front page held, ride it — post update comment with "wow, thanks" + roadmap |
| 12–24h | Submit Product Hunt draft; submit newsletters |
| 24–48h | Triage issues, merge easy PRs, tweet "peek hit X stars, thank you" with new demo |

### Issue triage

- [ ] Label issues: `bug`, `enhancement`, `good first issue` (attracts contributors)
- [ ] Fix `pip install` / crash bugs within hours — every broken install is a lost star
- [ ] Add "good first issue" for easy wins (e.g., "add entry heuristic for X framework")

### Metrics to watch

| Metric | Check where | Target day 1 | Target week 1 |
|---|---|---|---|
| GitHub stars | `github.com/YOU/peek` | 200–800 | 1k+ |
| PyPI downloads | `pypistats.org/packages/peek` | 100–500 | 2k+ |
| HN rank | `hn.algolia.com` or manual | Top 30 → top 10 | — |
| Twitter impressions | Analytics | 10k+ | 50k+ |
| Issues/PRs | GitHub | 5+ | 20+ |

---

## 8. If Launch Stalls — Playbook B

### If HN doesn't hit front page

- Don't panic — 70% of Show HN posts don't hit front page. You still get 20–100 stars + feedback.
- Re-launch in 1 week with new angle: "Show HN: peek — I mapped 100 famous repos, here's what I learned" (content marketing).
- Double down on Twitter + Reddit — they don't depend on HN.

### If Twitter gets no traction

- Your GIF might be too long or not autoplay. Re-cut to 10 sec, < 2MB, 800px, first frame is the wow.
- Repost with different hook: "The most beautiful `tree` replacement you'll see today" (curiosity gap).

### If GitHub stars stall at 200

- That's still success — 200 stars week 1 is top 5% of launches. Keep shipping: `peek --pack`, `peek --find` in v0.2.0 gives you a second launch.

---

## 9. Templates — Copy-Paste

### Star thank-you tweet (when you hit 500 stars)

```
peek hit 500 stars in 24h 🎉

Thank you! The most requested features are:
- peek --pack (ranked LLM context)
- peek --explain (traceback explainer)
- HTML graph viz

Shipping v0.2.0 this week. What else do you want?

[GitHub link]
```

### Issue response template

```
Thanks for reporting! Good catch — fixing in v0.1.1.

If you'd like to contribute, this is a great first issue:
[link to good first issue]

Would love a PR!
```

---

## 10. Calendar — At a Glance

| Day | Date (example) | Action |
|---|---|---|
| 1–5 | Mon–Fri | Build (see `06_five_day_build_plan.md`) |
| 5 eve | Fri eve | Polish, draft posts, rest |
| 6 | Sat | **Don't launch** — test on friend's machine, fix bugs |
| 7 | Sun | Final check, schedule posts |
| 8 | **Mon 08:00 UTC** | 🚀 HN Show HN + Twitter + Reddit |
| 9 | Tue | Product Hunt + newsletters |
| 10–14 | Wed–Sun | Triage, ship v0.1.1, tweet updates |

**The best launch day is Tuesday or Wednesday.** If you finish Fri, wait until Tue.

---

*This playbook is your launch checklist. Print it, check boxes, don't skip the 2-hour reply window — that's where trending is won or lost.*

---

*Pack complete. See `01_research_overview.md` for the map. Now go build `peek`.*


---
*Author: **Hariom Lohar** -- hariomlohar.new@gmail.com -- https://hariomlohardev.github.io/ -- 2026-08-10*

