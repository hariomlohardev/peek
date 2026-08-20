# Changelog

All notable changes to `peek` will be documented here.

## 0.5.0 — 2026-08-20
- **trace v2** — `peek trace` minimal aesthetic terminal UI (quiet hierarchy, accent only on focal, `takes → assign`, `● param ◆ local ◇ literal`, `↺ recursive`, `↗ external`, `Panel ROUNDED` `dim line` `padding (1,2)`, `Tree guide_style dim line`) + premium `--html` viewer (glass hero, file pills, instant 10-theme switch without reload, `localStorage`, search highlight, `copy JSON/Save`, sticky file side-panel, `file://` safe)
- **--html flag** — `peek trace --html` temp HTML + `webbrowser.open`, `peek trace --html -o trace.html`, polished self-contained `peek/trace/html.py` (412 → 509 lines, 42K)
- **CLI polish** — `symbol` (`name|MyClass.method|file::func|module:func`) / `--at FILE:LINE` / `--depth 1-6` / `--direction callees|callers|both` / `--cross-file/--local` / `--show-externals` / `--json`/`--output`/`--html`/`--theme`, Windows `C:\` safe, `•` leaf, `cycle` detection
- **Terminal** — `peek/peek/trace/render.py` rewritten (278 lines → 182 insertions, `All checks passed`, `163 passed`)
- **Docs** — `README.md` + `peek/README.md` trace quick-start + features table updated for 5.0, `CHANGELOG 0.5.0`
- **Release** — `pyproject.toml` `0.5.0`, `twine` upload, `git tag v5.0.0`, `gh release create`

## 0.4.0 — 2026-08-18
- `trace` Python-only function tree — `peek trace` (flag, not TUI) `peek/trace/` (`models.py` `python.py` `builder.py` `query.py` `render.py` `html.py`): `FuncId`/`FuncNode`/`CallSite`/`TraceGraph`, 2-pass `ast` (decl + per-file call extraction `extract_calls_per_file`), `CallVisitor` with `PARAM_THROUGH|LITERAL|LOCAL_RESULT` + `assign_target`, resolver (same-file → import alias → module_index → external/builtin), `trace(graph, focal, depth=1-6, direction=callees|callers|both, cross_file, show_externals)` with cycle `↺` detection
- CLI `peek trace` — `symbol` (`name`|`MyClass.method`|`file::func`|`module:func`) or `--at FILE:LINE`, `--depth` 1-6, `--direction`, `--cross-file/--local`, `--show-externals`, `--json`/`--output`, `--html` (temp HTML + `webbrowser.open`, polished self-contained `build_trace_html` with 10-theme tokens, file chips, `takes → assign · L`, filter/expand/copy, `localStorage` theme), `--theme`; Python-only for now, later JS/TS/Go/Rust via `tree-sitter`; `pip install -e "."` or `pip install -e ".[dev]"` (no extra deps)
- Design/UI — minimal editorial `render_trace` (`ROUNDED` `line` `bg`, `ink`/`muted`/`cyan`/`accent` hierarchy, `takes` line with `PARAM_THROUGH` highlight, file chips, `takes → assign · L`, cycle `↺`), `build_trace_html` polished viewer (sticky header, `focal` pill, stats `nodes·files·depth`, `ul.tree` with `▾` toggle, search `/`, `e`/`c` expand, 10-theme picker, responsive/print, `file://` safe)
- Docs — `README.md` + `peek/README.md` `trace` quick-start + features table, `CHANGELOG.md` 0.4.0

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

