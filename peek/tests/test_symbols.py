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


def test_symbols_go():
    """Go functions, methods and types land in the index."""
    from peek.scanner import scan
    from peek.symbols import index_symbols
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "a.go").write_text(
            "package main\n"
            "\n"
            "import \"fmt\"\n"
            "\n"
            "type Server struct {\n"
            "\tAddr string\n"
            "}\n"
            "\n"
            "type Handler interface {\n"
            "\tServe()\n"
            "}\n"
            "\n"
            "func Foo() {\n"
            "\tfmt.Println(\"hi\")\n"
            "}\n"
            "\n"
            "func (s *Server) Start(addr string) error {\n"
            "\treturn nil\n"
            "}\n"
            "\n"
            "func Map[T any](xs []T) []T {\n"
            "\treturn xs\n"
            "}\n"
        )
        syms = index_symbols(scan(p))
        by_name = {s.name: s for s in syms}

        assert "Foo" in by_name, f"expected Foo, got {sorted(by_name)}"
        assert by_name["Foo"].kind == "def"
        assert by_name["Foo"].lineno == 13
        assert by_name["Foo"].file.name == "a.go"

        assert by_name["Start"].kind == "def", "method with a receiver was missed"
        assert by_name["Map"].kind == "def", "generic function was missed"
        assert by_name["Server"].kind == "class"
        assert by_name["Handler"].kind == "class"


def test_symbols_go_ignores_closures_and_comments():
    """Only column-0 declarations count.

    Without the line anchor a closure assigned to a variable, or a
    commented-out function, would be indexed as a top-level symbol.
    """
    from peek.scanner import scan
    from peek.symbols import index_symbols
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "a.go").write_text(
            "package main\n"
            "\n"
            "// func Removed() {}\n"
            "\n"
            "func Real() {\n"
            "\thandler := func Inner() {}\n"
            "}\n"
        )
        names = {s.name for s in index_symbols(scan(p))}

        assert "Real" in names
        assert "Removed" not in names, "a commented-out func was indexed"
        assert "Inner" not in names, "a nested closure was indexed as top-level"
