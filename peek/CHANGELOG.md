# Changelog

All notable changes to `peek` will be documented here.

## 0.1.0 — 2026-08-10

**Initial release — htop for codebases**

- **Scanner** (`peek scan`): walk respecting `.gitignore`, languages + LOC + bar, tech stack (`pyproject.toml`/`package.json`), entry points (`main.py`/`pyproject.scripts`/`__main__` guard)
- **Analyzer** (`peek analyze`): AST import graph (relative + `src/` layout), PageRank + in-degree + entry bonus ranking, heuristic summary (FastAPI/Django/Typer/etc.)
- **Renderer** (`peek --no-tui`): 4 Rich panels (Summary, Tech Stack, Start Here, Graph) + Languages + Largest Files, `build_html` self-contained export
- **TUI** (`peek`): Textual `PeekApp` — Header, filter (`/`), nav (`j/k`), open in `$EDITOR` (`o`), details, `q` quit, fallback to static if not a tty
- **P1 Features**: `--html -o`, `--pack [--ask]`, `find` (filename+content ranked), `--llm` (OpenAI/Anthropic if key set)
- **Tests**: `test_scanner`, `test_analyzer`, `test_renderer_pack_find` — fixtures, BOM, circular, huge, empty, non-python
- **Packaging**: `pyproject.toml` (hatchling), `pip install peek`, `pipx`/`uv` ready, `peek` script
- **Docs**: `README` with GIF, install, usage, examples, comparison, `CONTRIBUTING`, `LICENSE` (MIT)

Built by [Hariom Lohar](https://hariomlohardev.github.io/).

[0.1.0]: https://github.com/hariomlohardev/peek/releases/tag/v0.1.0
