# Changelog

All notable changes to `peek` will be documented here.

## 0.3.0 — 2026-08-14
- `polyglot` graph — Python AST + JavaScript/TypeScript `import`/`require` regex (`peek/analyzer.py` `JS_IMPORT_RE`), no hard dep, `symbols` index `peek/symbols.py` (AST + `JS_EXPORT_RE`, BOM-tolerant)
- `peek graph --format svg` — `peek/graph.py` `export_graph` DOT/SVG/HTML (`build_dot` top15, `build_svg` `dot -Tsvg` or fallback), `peek graph --format dot|svg|html -o out.svg` (`exit 2` on unknown)
- `semantic` — `peek/embeddings.py` BM25 (`build_index` 30→50 chunks, `idf*tf`) + optional `fastembed` (`sentence-transformers/all-MiniLM-L6-v2`), `peek find "auth token" --semantic` and `peek --pack --ask "auth token" --semantic` + `peek index --rebuild` (`.peek/index.json`)
- `pack 3.0` — `tiktoken` `cl100k_base` accurate (`estimate_tokens`), `--clip` (`pyperclip`), `--dry-run` table, `--diff HEAD`/`--staged` (`git diff --name-only`), URL fetch `https://...tar.gz` (`urllib`→`curl`, tar/zip/plain, `tempfile.mkdtemp`), `--format md/xml/txt --budget --include/--exclude`
- `peek mcp` — MCP server (stdio) for Claude Code: exposes `scan`/`analyze`/`find`/`graph`/`pack` via `mcp` lib optional (Task 5, fallback hint)
- Viral polish: README hero with `polyglot` + `semantic` + `peek graph --format svg` + `peek find "auth token" --semantic` + `peek mcp`, `pip install peek-code`, docs sections `Symbols`/`Semantic`/`Graph`/`Git`/`MCP`, GIF regenerated (800×450, <3MB, 10 scenes)
- Tests: 129 passed, 1 skipped (added `test_symbols`/`test_embeddings`/`test_graph`/`test_pack_v3`)

## 0.2.1 — 2026-08-14
- fix: `peek .` now works — TyperGroup parse_args correctly routes path vs subcommand (fixes "No such command '.'")
- `peek myrepo` (existing dir) works, typos still error as unknown command
- tests: add `test_cli_dot` (5) — 113 passed, 1 skipped

## 0.2.0 — 2026-08-12
- `wtf`: traceback explainer with scan-aware hints
- `pack v2`: format md/xml/txt, budget, include/exclude globs
- `config set/get/list`: persistent theme with validation
- `watch`: polling + Textual toggle
- `t` live theme cycling in TUI
- Viral polish: README hero with wtf/watch, docs sections, GIF refreshed

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

