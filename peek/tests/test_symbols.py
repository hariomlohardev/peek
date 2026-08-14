"""Tests for Task 1 — Polyglot Graph JS/TS + symbol index."""

import tempfile
import pathlib


def test_symbols_js_import():
    from peek.symbols import index_symbols
    from peek.scanner import scan
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "a.js").write_text("import { foo } from './b.js';\nexport function bar() {}\n")
        (p / "b.js").write_text("export const foo = 1;\n")
        sr = scan(p)
        syms = index_symbols(sr)
        assert any(s.name == "bar" for s in syms)
        assert any(s.file.name == "a.js" for s in syms)


def test_polyglot_graph_js():
    from peek.scanner import scan
    from peek.analyzer import analyze
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "a.js").write_text("import x from './b.js';\n")
        (p / "b.js").write_text("export default 1;\n")
        sr = scan(p)
        ar = analyze(sr)
        assert ar.stats["graph_nodes"] >= 2 or len(ar.graph) >= 1  # was 0 before for JS
