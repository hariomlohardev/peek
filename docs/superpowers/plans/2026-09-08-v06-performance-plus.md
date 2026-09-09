# v0.6 Performance+ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship peek 0.6.0 — a measurably faster scanner plus three small features (MCP trace tool, serve auto-refresh, Go import graph) — on branch `feat/v0.6`, with tests green and docs/changelog/version bumped.

**Architecture:** No new subsystems. Each task is a focused change inside one existing module (scanner single-pass read, one new MCP tool branch reusing the CLI trace pipeline, one meta-tag injection in serve, one regex language in analyzer), verified by the existing suite plus small new tests, finished with a release-chores task.

**Tech Stack:** Python 3.11+ (stdlib only for all changes — `re`, `urllib` already used; no new dependencies), TypeScript untouched, pytest + `python -m ruff` for verification.

**Spec:** No separate spec doc — goals were set directly in the user request of 2026-09-08 (faster, "more good new things", branch-based). Non-goals are listed below instead of a spec file.

## Global Constraints

- Python floor: `requires-python = ">=3.11"` (do not use 3.12+ syntax).
- Ruff: line-length 100, select `E,F,I,B,SIM`, ignore `E501` — new/edited code must be `ruff check` + `ruff format` clean (run `python -m ruff`, the `ruff` shim is broken under PowerShell).
- Never crash: every scan/analyze path handles binary, huge, empty, permission-denied, `SyntaxError`, non-Python files by degrading, never raising to the CLI.
- Zero new runtime dependencies (stdlib only).
- No `Co-Authored-By` trailers in commit messages (repo policy, enforced by `.githooks/commit-msg`).
- Work on branch `feat/v0.6` only; do NOT push to `main`, do NOT create the `v0.6.0` tag (maintainer release step).
- Pytest cwd is the git root (`D:/peek/peek`); tests use `PYTHONPATH=peek`. Full suite: `$env:PYTHONPATH="peek"; python -m pytest peek/tests -q -p no:cacheprovider`. This sandbox sets `NO_COLOR=1`, which makes `test_render_static_animates_on_a_terminal` fail — that is environmental, not a regression (it passes with `NO_COLOR` unset).

## Non-goals

- tree-sitter, TUI redesign, shell completions (blocked: `_PeekGroup` swallows `--show-completion`), Rust import graph (stretch only), refreshing store manifests (they must follow the `v0.6.0` tag, which is out of scope).

## Baseline numbers (measured 2026-09-08, Windows, Python 3.13, 10k tiny files)

- `scan` (`max_files=20000`): ~135–155 s. Profile: **92% is file opens** — `_is_binary` opens+reads, `_count_loc` opens+reads again, `_has_main_guard` (via `detect_entry_points`) reads every `.py` a third time (~3 opens/file, ~4 ms each under antivirus).
- `analyze` (10k nodes): ~36 s (not in scope).

## File map

| Task | Files |
|---|---|
| 1 branch+baseline | git only: `git checkout -b feat/v0.6`; record bench via `PEEK_BENCH=1 pytest peek/tests/test_benchmark.py -s` |
| 2 single-pass scanner | Modify `peek/peek/scanner.py` (`_is_binary:151`, `_count_loc:166`, `_has_main_guard:455`, `detect_entry_points:495`, `scan:601`); Test `peek/tests/test_scanner.py` (append) |
| 3 benchmark proof+docs | Run bench; Modify `docs.md` Performance table |
| 4 MCP peek_trace | Modify `peek/peek/mcp_server.py` (TOOLS dict, `handle_tool:111`, module docstring line 6); Modify `peek/tests/test_mcp.py` (append); Modify `docs.md` MCP tools table; Modify `smithery.yaml` tools list |
| 5 serve --reload | Modify `peek/peek/serve.py` (`ReportServer`, `rebuild`); Modify `peek/peek/cli.py` `serve_command`; Test `peek/tests/test_serve.py` (append) |
| 6 Go import graph | Modify `peek/peek/analyzer.py` (JS block ~`build_graph`, `JS_IMPORT_RE:61` area); Test `peek/tests/test_analyzer.py` (append) |
| 7 release 0.6.0 | Modify `peek/peek/__init__.py` (`__version__`), `peek/pyproject.toml` (version), `CHANGELOG.md` (new section), root `README.md` + `peek/README.md` badges, `docs.md` if numbers changed |
| 8 green+push | Full suite + ruff on touched files, commit per task, `git push -u origin feat/v0.6` |

---

### Task 1: Branch and baseline

**Files:**
- Create: (none — git branch `feat/v0.6` from `main`)
- Test: `peek/tests/test_benchmark.py` (existing, run-only)

**Interfaces:**
- Consumes: `origin/main` at `af6b803` (pushed, clean tree)
- Produces: branch `feat/v0.6`; baseline numbers written into this plan's Task 3 step

- [ ] **Step 1: Create the branch from a clean tree**

```bash
git -C D:\peek\peek status --short
git -C D:\peek\peek checkout -b feat/v0.6
```

Expected: `status --short` prints nothing (clean); branch created. If dirty, stop and report.

- [ ] **Step 2: Record the benchmark baseline (background, ~4 min)**

```bash
$env:PYTHONPATH="peek"; $env:PEEK_BENCH="1"; python -m pytest peek/tests/test_benchmark.py -q -p no:cacheprovider -s
```

Expected: 3 passed; note the printed `scan 10k files: Ns` and `analyze 10k files: Ns` lines. Write them into Task 3's docs edit. (Known: ~135–155 s scan, ~36 s analyze on the Windows sandbox.)

- [ ] **Step 3: Commit nothing (branch creation is the deliverable)**

Verify with `git -C D:\peek\peek log --oneline -1` (still `af6b803`) and `git branch --show-current` → `feat/v0.6`.

---

### Task 2: Single-pass scanner

**Files:**
- Modify: `peek/peek/scanner.py`
- Test: `peek/tests/test_scanner.py` (append one test)

**Interfaces:**
- Consumes: `scan(root, max_files=2000) -> ScanResult` (unchanged signature); `ScanResult.stats` keys `total_files`, `total_loc`, `truncated` (unchanged)
- Produces: same `scan` behavior with ~1 open per file; helper `_read_file_bytes(path, cap=1_000_000) -> bytes | None`

Design: add `_read_file_bytes` (one `open('rb')`, reads up to cap, returns `None` on `OSError`/permission). Rewrite the three consumers to take bytes: `_is_binary(data: bytes) -> bool` (null-byte check, same rule as today), `_count_loc(data: bytes) -> int` (same counting on decoded text, `errors="ignore"`), `_has_main_guard_text(text: str) -> bool` (same `__name__` check, no file IO). In `scan`'s per-file loop, call `_read_file_bytes` once and pass the bytes to all three. Keep the old names working: if `test_scanner.py` imports `_is_binary`/`_count_loc` directly with paths, keep thin path-taking wrappers with the same names that read-then-delegate (check imports first with grep).

- [ ] **Step 1: Check what test_scanner imports**

Run: `Select-String -Path D:\peek\peek\peek\tests\test_scanner.py -Pattern "import|_is_binary|_count_loc|_has_main_guard"`
Expected: list of imports. If tests call `_is_binary(path)` / `_count_loc(path)` with paths, keep same-name wrappers.

- [ ] **Step 2: Write the failing test** (append to `peek/tests/test_scanner.py`)

```python
def test_scan_single_pass_entry_and_loc(tmp_path):
    """Single-pass read must still detect the __main__ guard and count LOC."""
    from peek.scanner import scan

    p = tmp_path / "repo"
    p.mkdir()
    (p / "run.py").write_text('import os\n\ndef main():\n    pass\n\nif __name__ == "__main__":\n    main()\n', encoding="utf-8")
    sr = scan(p)
    assert sr.total_files == 1
    assert sr.stats["total_loc"] == 6
    assert any("run.py" in str(c) for c in sr.entry_candidates)
```

- [ ] **Step 3: Run it (passes before AND after — it pins behavior, not speed)**

Run: `$env:PYTHONPATH="peek"; python -m pytest peek/tests/test_scanner.py -q -p no:cacheprovider`
Expected: PASS (baseline pin).

- [ ] **Step 4: Implement the single-pass read in `peek/peek/scanner.py`**

Replace the per-file double open (`_is_binary(path)` then `_count_loc(path)`) with one `_read_file_bytes` call feeding both, and make `detect_entry_points` reuse the already-read text for `.py` files instead of re-reading via `_has_main_guard(path)`. Keep public behavior identical (same stats keys, same ignore rules, same never-crash `try/except` around IO).

- [ ] **Step 5: Run scanner + analyzer + full affected tests**

Run: `$env:PYTHONPATH="peek"; python -m pytest peek/tests/test_scanner.py peek/tests/test_analyzer.py peek/tests/test_comprehensive_tdd.py -q --tb=short -p no:cacheprovider`
Expected: all PASS.

- [ ] **Step 6: Ruff the touched files**

Run: `python -m ruff check peek/peek/scanner.py peek/tests/test_scanner.py; python -m ruff format --check peek/peek/scanner.py peek/tests/test_scanner.py`
Expected: clean. Fix or hand-fix-until-clean (do NOT reformat unrelated lines).

- [ ] **Step 7: Commit**

```bash
git -C D:\peek\peek add peek/peek/scanner.py peek/tests/test_scanner.py
git -C D:\peek\peek commit -m "perf: single-pass file reads in scanner"
```

---

### Task 3: Benchmark proof + docs numbers

**Files:**
- Modify: `docs.md` (Performance → 10k table)
- Test: `peek/tests/test_benchmark.py` (run-only)

**Interfaces:**
- Consumes: Task 2's faster `scan`; bench prints `scan 10k files: Ns`
- Produces: updated `docs.md` table row with the NEW measured numbers

- [ ] **Step 1: Re-run the benchmark (background, ~2–4 min)**

```bash
$env:PYTHONPATH="peek"; $env:PEEK_BENCH="1"; python -m pytest peek/tests/test_benchmark.py -q -p no:cacheprovider -s
```

Expected: 3 passed. Target: scan ≤ 60 s on the same machine (≥2x faster). If slower than baseline, stop — the single-pass regressed, do not update docs, report back.

- [ ] **Step 2: Update the docs table with measured numbers**

```markdown
| `scan` (`max_files=20000`) | ~Ns (was ~135–155 s before single-pass reads) |
| `analyze` (10k nodes) | ~36 s (unchanged) |
```

Keep the takeaway sentence about the 2000 cap. Use the REAL printed numbers, not the target.

- [ ] **Step 3: Commit**

```bash
git -C D:\peek\peek add docs.md
git -C D:\peek\peek commit -m "docs: update 10k benchmark numbers for 0.6"
```

---

### Task 4: MCP `peek_trace` tool

**Files:**
- Modify: `peek/peek/mcp_server.py` (TOOLS dict ~line 19–90, `handle_tool:111`, docstring line 6)
- Modify: `peek/tests/test_mcp.py` (append; check its imports/shape first)
- Modify: `docs.md` (MCP tools table — add one row), `smithery.yaml` (tools list — add one line)

**Interfaces:**
- Consumes: `build_trace_graph(scan_result)` (`peek.trace`), `find_focals(graph, symbol, limit=5)`, `find_by_location(graph, file_query, lineno)`, `trace(graph, focal, depth=3, direction="callees", cross_file=True, show_externals=False)`, `trace_to_json(trace_tree, graph)` (`peek.trace.render`) — the exact pipeline `trace_command` in `peek/peek/cli.py:769-891` uses
- Produces: `handle_tool("peek_trace", args) -> dict` (JSON-serializable payload or `{"error": ...}`; never raises)

Tool schema: `{path?: string, symbol?: string, at?: "FILE:LINE", depth?: int (1-6, default 3), direction?: "callees"|"callers"|"both", cross_file?: bool, show_externals?: bool}`. Focal resolution order: `at` (split on last `:` for line) → `symbol` via `find_focals` (first hit; empty → `{"error": "no match"}`) → neither → `{"error": "pass symbol or at"}`. Clamp depth to 1–6.

- [ ] **Step 1: Read test_mcp.py shape**

Read `D:\peek\peek\peek\tests\test_mcp.py` (need exact helper names before writing tests).

- [ ] **Step 2: Write the failing tests** (append)

```python
def test_peek_trace_tool(tmp_path):
    from peek.mcp_server import handle_tool

    p = tmp_path / "repo"
    p.mkdir()
    (p / "a.py").write_text("import b\n\ndef main():\n    b.work()\n", encoding="utf-8")
    (p / "b.py").write_text("def work():\n    return 1\n", encoding="utf-8")
    res = handle_tool("peek_trace", {"path": str(p), "symbol": "main", "depth": 2})
    assert "error" not in res, res
    assert res["focal"] is not None


def test_peek_trace_tool_no_match(tmp_path):
    from peek.mcp_server import handle_tool

    p = tmp_path / "repo"
    p.mkdir()
    (p / "a.py").write_text("x = 1\n", encoding="utf-8")
    res = handle_tool("peek_trace", {"path": str(p), "symbol": "nope_nothing"})
    assert "error" in res
```

- [ ] **Step 3: Run to verify they fail**

Run: `$env:PYTHONPATH="peek"; python -m pytest peek/tests/test_mcp.py -q -p no:cacheprovider`
Expected: FAIL with `Unknown tool 'peek_trace'`.

- [ ] **Step 4: Implement** — add the `peek_trace` TOOLS entry, the `handle_tool` branch (reuse the `trace_command` pipeline: scan → `build_trace_graph` → resolve focal → `trace(...)` → `trace_to_json(...)`; wrap everything so it returns `{"error": str}` instead of raising), and update the module docstring tool list.

- [ ] **Step 5: Run tests + ruff**

Run: `$env:PYTHONPATH="peek"; python -m pytest peek/tests/test_mcp.py -q --tb=short -p no:cacheprovider`
Expected: all PASS. Then `python -m ruff check peek/peek/mcp_server.py peek/tests/test_mcp.py` clean.

- [ ] **Step 6: Docs + smithery**

Add the `peek_trace` row to the `docs.md` MCP tools table (same columns: name, description, arguments) and to the `smithery.yaml` tools list.

- [ ] **Step 7: Commit**

```bash
git -C D:\peek\peek add peek/peek/mcp_server.py peek/tests/test_mcp.py docs.md smithery.yaml
git -C D:\peek\peek commit -m "feat: add peek_trace MCP tool"
```

---

### Task 5: Serve `--reload` auto-refresh

**Files:**
- Modify: `peek/peek/serve.py` (`ReportServer.__init__`, `rebuild`)
- Modify: `peek/peek/cli.py` (`serve_command`)
- Test: `peek/tests/test_serve.py` (append)

**Interfaces:**
- Consumes: `ReportServer(root, port=4181, open_browser=False, theme=None, directory=None, watch=True)` (existing)
- Produces: `ReportServer(..., reload_sec: int = 0)`; when `> 0`, served `index.html` contains `<meta http-equiv="refresh" content="N">` right after `<head...>` (regex once, prepend fallback); CLI flag `--reload` (int seconds, default 0)

- [ ] **Step 1: Write the failing tests** (append to `peek/tests/test_serve.py`)

```python
def test_serve_reload_injects_meta(tmp_path):
    from peek.serve import ReportServer

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("x = 1\n", encoding="utf-8")
    server = ReportServer(repo, port=0, watch=False, directory=tmp_path / "out", reload_sec=2)
    server.start()
    try:
        html = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
        assert '<meta http-equiv="refresh" content="2">' in html
    finally:
        server.stop()


def test_serve_no_reload_by_default(tmp_path):
    from peek.serve import ReportServer

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("x = 1\n", encoding="utf-8")
    server = ReportServer(repo, port=0, watch=False, directory=tmp_path / "out")
    server.start()
    try:
        html = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
        assert "http-equiv=\"refresh\"" not in html
    finally:
        server.stop()
```

- [ ] **Step 2: Run to verify they fail**

Run: `$env:PYTHONPATH="peek"; python -m pytest peek/tests/test_serve.py -q -p no:cacheprovider`
Expected: FAIL (`reload_sec` unexpected keyword).

- [ ] **Step 3: Implement** — `reload_sec` param + injection in `rebuild()` + `--reload` CLI option on `serve_command` (also add to the `serve --help` example line `peek serve --open --reload 2`).

- [ ] **Step 4: Run tests + ruff**

Run: `$env:PYTHONPATH="peek"; python -m pytest peek/tests/test_serve.py -q --tb=short -p no:cacheprovider`
Expected: all PASS. Then ruff check both files clean.

- [ ] **Step 5: Commit**

```bash
git -C D:\peek\peek add peek/peek/serve.py peek/peek/cli.py peek/tests/test_serve.py
git -C D:\peek\peek commit -m "feat: add serve --reload auto-refresh"
```

---

### Task 6: Go import graph

**Files:**
- Modify: `peek/peek/analyzer.py` (`build_graph`, near `JS_IMPORT_RE:61` and the javascript/typescript branch ~line 300)
- Test: `peek/tests/test_analyzer.py` (append)

**Interfaces:**
- Consumes: `scan()` already tags Go files (`f.language == "go"`, `symbols.py` proves detection); existing `_resolve_local_import`-style suffix matching
- Produces: `build_graph` handles `f.language == "go"`: `graph_nodes >= 2` and a resolved edge on a tiny Go repo

Go imports: single-line `import "fmt"` / `import alias "x/y"` and blocks `import ( "a" \n b "c/d" )`. Local packages match by trailing path segments against scanned `.go` files (same suffix strategy the JS resolver uses). Stdlib/short names with no match → external (do not create nodes, do not crash). Keep it regex-only like JS — no tree-sitter.

- [ ] **Step 1: Write the failing test** (append to `peek/tests/test_analyzer.py`; check its tmp-repo helper style first — it builds temp dirs with `(p / "a.py").write_text(...)`)

```python
def test_go_import_graph(tmp_path):
    from peek.analyzer import analyze
    from peek.scanner import scan

    p = tmp_path / "repo"
    (p / "go.mod").write_text("module example.com/t\n\ngo 1.21\n", encoding="utf-8")
    (p / "a.go").write_text('package t\n\nimport "example.com/t/b"\n\nfunc A() { b.B() }\n', encoding="utf-8")
    (p / "b").mkdir()
    (p / "b" / "b.go").write_text("package b\n\nfunc B() {}\n", encoding="utf-8")
    ar = analyze(scan(p))
    assert len(ar.graph) >= 2
    assert any("a.go" in str(k) for k in ar.graph)
```

- [ ] **Step 2: Run to verify it fails**

Run: `$env:PYTHONPATH="peek"; python -m pytest peek/tests/test_analyzer.py::test_go_import_graph -q -p no:cacheprovider`
Expected: FAIL (Go files get no graph nodes today).

- [ ] **Step 3: Implement** — `GO_IMPORT_RE` + a `go` branch in `build_graph` mirroring the JS branch (extract quoted import paths, resolve locals by path-suffix match, rest external). Rust: check — if `mod`/`use` resolution fits the same 20-line shape, include it; otherwise leave Rust to symbols-only and say so in the commit message.

- [ ] **Step 4: Run analyzer + symbols + graph tests + ruff**

Run: `$env:PYTHONPATH="peek"; python -m pytest peek/tests/test_analyzer.py peek/tests/test_symbols.py peek/tests/test_graph.py -q --tb=short -p no:cacheprovider`
Expected: all PASS. Then ruff check clean on both files.

- [ ] **Step 5: Commit**

```bash
git -C D:\peek\peek add peek/peek/analyzer.py peek/tests/test_analyzer.py
git -C D:\peek\peek commit -m "feat: add Go import graph"
```

---

### Task 7: Release 0.6.0 chores

**Files:**
- Modify: `peek/peek/__init__.py` (`__version__ = "0.5.0"` → `"0.6.0"`), `peek/pyproject.toml` (`version = "0.5.0"` → `"0.6.0"`), `CHANGELOG.md` (prepend `## 0.6.0` section), root `README.md` + `peek/README.md` (tests badge counts), `docs.md` (only if Task 3 numbers need a second touch)

**Interfaces:**
- Consumes: measured bench numbers (Task 3), final `pytest` passing count
- Produces: consistent 0.6.0 version everywhere code-side; manifests deliberately UNCHANGED (they must follow the `v0.6.0` tag + real tarball hash — maintainer release step, noted in CHANGELOG)

- [ ] **Step 1: Bump the version in both files**

`peek/peek/__init__.py`: `__version__ = "0.6.0"`. `peek/pyproject.toml`: `version = "0.6.0"`.

- [ ] **Step 2: CHANGELOG entry** (prepend after the `# Changelog` + intro lines)

```markdown
## 0.6.0 — 2026-09-08
- **perf** — scanner single-pass reads (binary + LOC + main-guard from one open): 10k-file scan ~Ns (was ~135–155 s)
- **mcp** — new `peek_trace` tool (function call tree for agents: symbol/at + depth/direction)
- **serve** — `--reload SEC` auto-refresh for the live dashboard
- **polyglot** — Go import graph (regex, offline); JS/TS unchanged
- **release** — version 0.6.0; store manifests refresh follows the `v0.6.0` tag (needs real tarball hash)
```

Use the REAL bench number from Task 3.

- [ ] **Step 3: README badges** — get the real passing count from Task 8's full run first, then set the `tests-N-passed` badges in both READMEs to it (they currently say 146/158, stale since long ago).

- [ ] **Step 4: Verify + commit**

Run: `$env:PYTHONPATH="peek"; python -m peek.cli --version` (must print `peek v0.6.0` — run from git root so local code wins).
Then:

```bash
git -C D:\peek\peek add peek/peek/__init__.py peek/pyproject.toml CHANGELOG.md README.md peek/README.md docs.md
git -C D:\peek\peek commit -m "chore: release 0.6.0 version bump and changelog"
```

---

### Task 8: Full green + push branch

**Files:** (none — verification + push)

- [ ] **Step 1: Full suite**

Run: `$env:PYTHONPATH="peek"; python -m pytest peek/tests -q --tb=short -p no:cacheprovider`
Expected: all pass except possibly `test_render_static_animates_on_a_terminal` (fails only when `NO_COLOR=1` is set in the environment — sandbox artifact; re-run that one test with `NO_COLOR` removed to confirm green).

- [ ] **Step 2: Ruff on every touched file**

Run: `python -m ruff check <each touched file>; python -m ruff format --check <each touched file>`
Expected: clean on new/edited code. Pre-existing violations in untouched regions stay untouched.

- [ ] **Step 3: Push the branch**

```bash
git -C D:\peek\peek log --oneline origin/main..HEAD
git -C D:\peek\peek push -u origin feat/v0.6
```

Expected: push succeeds; report the commit list. Do NOT merge to main, do NOT tag.

---

## Self-review

1. **Spec coverage:** user goals were (a) plan first — this doc; (b) performance — Tasks 2+3 with measured proof; (c) "more good new things" — Tasks 4, 5, 6 (agent tool, dashboard refresh, polyglot); (d) "update all the things" — Task 7 (version/changelog/badges/docs); (e) specific branch — Task 1 + all commits land on `feat/v0.6`, Task 8 pushes only the branch. No goal lacks a task.
2. **Placeholder scan:** every step names exact files, exact commands, exact expected output, and real code — no TBD/TODO/"similar to", no undescribed error handling (never-crash is a Global Constraint with exact semantics).
3. **Type consistency:** `scan(root, max_files)` / `ScanResult.stats` keys / `ReportServer(...)` params / `handle_tool(name, args) -> dict` / `build_trace_graph → find_focals/find_by_location → trace → trace_to_json` match the codebase as read 2026-09-08 (file:line anchors in the file map).
