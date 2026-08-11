# Changelog

All notable changes to `peek` will be documented here.

## 0.1.0 — 2026-08-11

- Initial release — `htop for codebases`
- Scanner: `.gitignore`-aware walk, 2000-file cap, binary/huge/symlink-safe, tech-stack + entry-point detection
- Analyzer: AST graph, relative + `src/` resolution, stdlib-filtered, PageRank + in-degree + entry bonus ranking, heuristic summary
- Renderer: Rich panels, themed static stagger (40/30 ms) + `build_html` self-contained
- TUI: Textual `PeekApp` with `linear` 220 ms fade, list stagger, `asyncio` filter, continuous pulse/tip/border, `peek --theme-list`
- 10 themes: anthropic-pro (default), cinematic, dracula, nord, catppuccin-mocha, tokyo-night, solarized-dark, github-dark, monokai, minimal-mono (15 tokens, `#RRGGBB`)
- CLI: `peek [PATH]`, `scan`/`analyze`/`find`, `--no-tui`/`--html`/`--pack`/`--ask`/`--llm`/`--find`, `--theme`/`--theme-list`, win32 `/tmp` safe, `SpinnerColumn(spinner_name="dots")`
- Pack/Find/LLM: token budget, ranked search, optional OpenAI/Anthropic
- Config: `PEEK_THEME` env + `~/.peek/config.toml` / `~/.config/peek/config.toml` / `$PEEK_CONFIG`
- Assets: `peek/assets/demo.gif` (800×450, Pillow code-generated, <3MB) + `demo.svg` (SMIL) + `demo.html` (themed)
- Tests: 74 passed, 1 skipped (TDD)
- Docs: `docs.md` + `master.md` + `peek/README.md` + 10 SVG previews

