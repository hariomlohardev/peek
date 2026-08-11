# Theme System Design — peek (htop for codebases)

**Date:** 2026-08-11
**Author:** Hariom Lohar
**Status:** Approved — Approach A (Central Registry)
**Branch strategy:** `themes-10` (from `design-anthropic`), 10 parallel worktrees → merge

## 1. Summary

Add 10 selectable themes to `peek` so users can choose their vibe. Same layout/animations across all themes — only color tokens change. Selection via `--theme` flag, `PEEK_THEME` env, and `~/.peek/config.toml` (or XDG). Default remains `anthropic-pro` (warm clay on charcoal) for professional polish. Exposes `peek --theme-list` for discovery.

## 2. Goals & Non-Goals

**Goals:**
- 10 themes, instantly switchable: `peek --theme dracula`, `PEEK_THEME=tokyo-night peek`, persisted via config.
- Works in TUI, static (`--no-tui`), and HTML export (`--html` embeds theme).
- One `git branch themes-10` tested locally, no push, 29 existing tests still pass, new theme tests added.
- Parallel agent implementation — each theme entry owned by one agent, no conflicts.

**Non-Goals:**
- User-custom themes / theming API (future: `peek/themes/*.py` plugin loader).
- Per-panel custom styling or animation per-theme tweaks — keep motion uniform (40–60ms stagger, 220ms fade).
- Auto-save on `--theme` — explicit `peek theme set <name>` later if demanded.

## 3. The 10 Themes (Locked)

| # | ID | Label | Accent → Bg | Muted | Ink | Vibe |
|---|----|-------|-------------|-------|-----|------|
| 1 | `anthropic-pro` | Anthropic Pro | `#D4A27F` → `#141413` | `#9A9590` | `#E8E6E3` | Warm editorial, default |
| 2 | `cinematic` | Cinematic | `#FFE600` → `#070A14` | `#8B8FA3` | `#E8E6E3` | Neon viral, yellow signal |
| 3 | `dracula` | Dracula | `#BD93F9` → `#282A36` | `#6272A4` | `#F8F8F2` | Purple haze, popular |
| 4 | `nord` | Nord | `#88C0D0` → `#2E3440` | `#4C566A` | `#ECEFF4` | Frost, arctic calm |
| 5 | `catppuccin-mocha` | Catppuccin Mocha | `#CBA6F7` → `#1E1E2E` | `#6C7086` | `#CDD6F4` | Pastel mauve, cozy |
| 6 | `tokyo-night` | Tokyo Night | `#7AA2F7` → `#1A1B26` | `#565F89` | `#C0CAF5` | Electric, storm |
| 7 | `solarized-dark` | Solarized Dark | `#268BD2` → `#002B36` | `#586E75` | `#EEE8D5` | Teal, classic |
| 8 | `github-dark` | GitHub Dark | `#58A6FF` → `#0D1117` | `#8B949E` | `#E6EDF3` | Familiar, OSS |
| 9 | `monokai` | Monokai | `#F92672` → `#272822` | `#75715E` | `#F8F8F2` | Hot pink/green pop |
| 10 | `minimal-mono` | Minimal Mono | `#E5E5E5` → `#111111` | `#8A8A8A` | `#E5E5E5` | Grayscale, a11y |

Each `tokens` dict contains: `bg, bg2, surface, panel, line, line2, ink, ink2, muted, muted2, accent, accent2, cyan, violet, green` (15 keys, uniform). Extra semantic aliases allowed but not required.

## 4. Architecture

### 4.1 Files

```
peek/peek/themes.py   NEW  — Theme dataclass, THEMES dict, get_theme, list_themes, resolve_theme
peek/peek/config.py   NEW  — load_config, get_config_theme, config_path()
peek/peek/renderer.py MOD  — remove ANTHRO constant, accept Theme param, use theme.tokens
peek/peek/tui.py      MOD  — remove ANTHRO, accept Theme, template CSS from tokens
peek/peek/animations.py MOD — tokens via get_theme()
peek/peek/cli.py      MOD  — add --theme, --theme-list, resolve before scan
peek/tests/test_themes.py NEW — 12+ tests for registry, resolve precedence, renderer/tui smoke per theme
```

### 4.2 Types

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Theme:
    id: str
    label: str
    description: str
    tokens: dict[str, str]  # 15 keys validated at import
    preview: str = "■"       # swatch char for --theme-list

THEMES: dict[str, Theme]  # keyed by id lower-case

def get_theme(name: str | None) -> Theme: ...  # fallback anthropic-pro
def list_themes() -> list[Theme]: ...           # sorted by id
def resolve_theme(cli_opt: str | None) -> Theme:  # cli > env > config > default
    ...
```

Validation at import: every theme must have exactly the 15 token keys, values are `#RRGGBB`, raises `ValueError` early if broken (test catches).

### 4.3 Resolve Precedence

```
resolve_theme(cli_opt):
  if cli_opt: return get_theme(cli_opt) or error
  if PEEK_THEME env: return get_theme(env) or error
  cfg = load_config()  # ~/.peek/config.toml or $XDG_CONFIG_HOME/peek/config.toml or ~/.config/peek/config.toml
  if cfg.get("theme"): return get_theme(cfg["theme"]) or fallback
  return THEMES["anthropic-pro"]
```

`load_config()` is tolerant: missing file → {}, parse error → {} + warning to stderr, never crash.

### 4.4 Wiring

- `cli.main_callback` / `scan_command` / `analyze_command` resolve theme first (before `scan()`), thread `theme` into `render_static(scan, analyzer, elapsed, console, theme)`, `build_html(..., theme)`, `run_tui(..., theme)`.
- `renderer.py`: replace `ANTHRO = {...}` with `theme.tokens` lookups. Keep function signatures backward compatible: `render_static(..., theme: Theme | None = None)` → `theme = theme or get_theme(None)`.
- `tui.py`: `PeekApp.__init__(..., theme)` stores, CSS is `f"""Screen {{background: {t['bg']}}}..."""` templated at init. No global.
- `animations.py`: `get_theme` used for spinner color.
- HTML: `build_html` embeds `background: {tokens['bg']}` in `<style>` and records correct fragment.

## 5. CLI / TUI UX

**CLI:**
- `peek --theme dracula` — one-shot
- `peek --theme-list` — prints table with swatches + exits 0 (no scan)
  ```
  Available themes:
    anthropic-pro  ■  Warm editorial (default)  #141413 → #D4A27F
    cinematic      ■  Neon viral
    ...
  ```
- `peek --theme dracula --no-tui` / `peek --theme tokyo-night --html -o out.html` — themed static/html
- Invalid: `peek --theme no-such` → `[red]Unknown theme 'no-such'. Available: anthropic-pro, cinematic, ...` exit 2
- `PEEK_THEME=dracula peek` — env override
- Config persistence: `~/.peek/config.toml`:
  ```toml
  # peek config — theme selection
  theme = "dracula"
  ```
  No auto-write; document `echo 'theme = "dracula"' > ~/.peek/config.toml`. Future `peek theme set dracula` can be added.

**TUI:**
- TUI respects resolved theme at launch. Future: press `t` to cycle (out of scope for 10-theme v1, but CSS templating makes it trivial).
- Footer hint: `Theme: dracula • --theme-list for more`

**Help:** `peek --help` shows `--theme TEXT` and `--theme-list`.

## 6. Config Handling

```python
# config.py
def config_path() -> Path:
    # 1. $PEEK_CONFIG env if set
    # 2. $XDG_CONFIG_HOME/peek/config.toml
    # 3. ~/.config/peek/config.toml (if exists)
    # 4. ~/.peek/config.toml (legacy, primary)
    ...

def load_config() -> dict:
    try: tomllib/tomli load
    except: return {}
```

Use `tomllib` (3.11+) with `tomli` fallback for 3.10 compat, though project requires 3.11+.

## 7. Testing Strategy

**Existing:** 29 tests must stay green.

**New `test_themes.py` (12 tests):**
- `test_registry_has_10` — `len(THEMES)==10`, ids match table
- `test_tokens_shape` — every theme has 15 keys, hex colors
- `test_get_theme_case_insensitive` — `get_theme("Dracula")==get_theme("dracula")`
- `test_get_theme_unknown_fallback` — unknown → anthropic-pro or raises? decided: raises ValueError, caller handles
- `test_resolve_precedence_cli_over_env_over_config` — monkeypatch env + tmp config
- `test_resolve_config_missing` — no file → default
- `test_render_static_all_themes_no_crash` — loop 10 themes, `Console(record, width=80)`, `render_static(..., theme)` no raise
- `test_build_html_all_themes_contains` — each html contains its bg hex
- `test_tui_css_per_theme` — `PeekApp(theme=...)` CSS contains bg
- `test_cli_theme_list` — `CliRunner.invoke(app, ["--theme-list"])` exit 0 and lists 10
- `test_cli_unknown_theme_exit2` — `["--theme","bogus"]` exit 2
- `test_config_toml_parse` — tmp config.toml → load_config correct

**Manual QA (peek --no-tui matrix):** Run `for t in anthropic-pro cinematic ...; do peek --theme $t --no-tui 2>&1 | head -5` and eyeball headers.

## 8. Parallel Agent Plan

**Branch:** `themes-10` from `design-anthropic` (already anthropic-pro). Never push.

**10 agents, each owns one theme entry in `themes.py` + its swatch/verification:**

- Orchestrator creates `peek/peek/themes.py` skeleton with `Theme` dataclass + 2 entries (anthropic-pro + cinematic as reference), and `config.py` stub.
- Then 10 worktrees (or 10 parallel edits with offset ranges) each append one theme dict entry:
  - Agent-1: dracula
  - Agent-2: nord
  - Agent-3: catppuccin-mocha
  - Agent-4: tokyo-night
  - Agent-5: solarized-dark
  - Agent-6: github-dark
  - Agent-7: monokai
  - Agent-8: minimal-mono
  - (anthropic-pro & cinematic done by orchestrator)
  - 2 agents handle wiring: `renderer.py` + `tui.py` theming, and `cli.py` + `config.py` + `--theme-list`

Simpler for this repo (single file contention): use **pipeline** with file locking — orchestrator writes skeleton, then agents each edit `themes.py` at distinct line ranges via `Edit` with exact `old_string` anchoring on previous theme entry, so merges are sequential but dispatched parallel with retry. Alternative: give each agent a worktree and merge with `git merge --no-ff` — chosen.

**Ordering:** skeleton → theme entries (parallel) → wiring (parallel) → tests → `pytest` + `peek --theme-list` smoke → commit.

## 9. Risks & Mitigations

- **Merge conflicts in themes.py:** Mitigate by each agent inserting after a unique anchor comment `# THEME: <id>`.
- **Rich/Textual color regression:** Mitigate by per-theme smoke test + visual `peek --no-tui` capture.
- **Config toml missing tomli:** Use `try: import tomllib except: import tomli` and graceful fallback.
- **Invalid theme crash:** Wrap `resolve_theme` in try, fallback with error message.

## 10. Future

- `peek theme set <name>` to persist, `peek theme preview` interactive gallery.
- Community themes via `peek/themes/*.py` discovery.
- `t` key in TUI to cycle live.

---

**Approval:** User approved Approach A and theme list on 2026-08-11. No further questions — proceed to implementation via writing-plans → workflow.
