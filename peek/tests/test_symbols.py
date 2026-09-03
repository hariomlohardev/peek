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
def test_symbols_rust():
    """Rust functions, methods, types and modules land in the index."""
    from peek.scanner import scan
    from peek.symbols import index_symbols
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "a.rs").write_text(
            "pub mod utils;\n"
            "\n"
            "pub struct Server {\n"
            "    addr: String,\n"
            "}\n"
            "\n"
            "pub enum State {\n"
            "    Idle,\n"
            "}\n"
            "\n"
            "pub trait Handler {\n"
            "    fn serve(&self);\n"
            "}\n"
            "\n"
            "fn bar() {}\n"
            "\n"
            "pub(crate) async fn fetch(url: &str) -> u32 {\n"
            "    0\n"
            "}\n"
            "\n"
            "impl Server {\n"
            "    pub fn start(&self) {}\n"
            "}\n"
        )
        sr = scan(p)
        syms = index_symbols(sr)
        by_name = {s.name: s for s in syms}

        # The acceptance criterion: `a.rs` with `fn bar()` is indexed.
        assert "bar" in by_name, "plain fn was not indexed"
        assert by_name["bar"].kind == "def"
        assert by_name["bar"].file.name == "a.rs"

        assert by_name["fetch"].kind == "def", "pub(crate) async fn was missed"
        assert by_name["start"].kind == "def", "method inside an impl block was missed"
        assert by_name["serve"].kind == "def", "trait method was missed"

        assert by_name["Server"].kind == "class"
        assert by_name["State"].kind == "class", "enum was missed"
        assert by_name["Handler"].kind == "class", "trait was missed"

        assert by_name["utils"].kind == "import", "mod declaration was missed"

        # Control: a name that is not declared anywhere must not appear, so the
        # assertions above can actually fail.
        assert "Nonexistent" not in by_name


def test_symbols_rust_ignores_comments_and_closures():
    """A commented-out fn is not a declaration.

    Indentation is deliberately allowed, because Rust methods live inside an
    `impl` block -- so the guard here is the `//`, not the column. Closures use
    `|x|` rather than `fn`, so they never reach the pattern in the first place.
    """
    from peek.scanner import scan
    from peek.symbols import index_symbols
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "a.rs").write_text(
            "// fn removed() {}\n"
            "    // fn also_removed() {}\n"
            "\n"
            "fn real() {\n"
            "    let add = |x: u32| x + 1;\n"
            "}\n"
        )
        sr = scan(p)
        names = {s.name for s in index_symbols(sr)}

        assert "real" in names, "control: the real fn must be indexed"
        assert "removed" not in names, "commented-out fn was indexed"
        assert "also_removed" not in names, "indented commented-out fn was indexed"
        assert "add" not in names, "a closure is not a fn declaration"


def test_symbols_rust_lineno_is_the_declaration_line():
    r"""The reported line is the `fn`, not a blank line above it.

    A `\s*` prefix would match from an earlier blank line and report the wrong
    number; `[ \t]*` is what keeps this honest.
    """
    from peek.scanner import scan
    from peek.symbols import index_symbols
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "a.rs").write_text("\n\n\nfn bar() {}\n")
        sr = scan(p)
        by_name = {s.name: s for s in index_symbols(sr)}

        assert by_name["bar"].lineno == 4, f"expected line 4, got {by_name['bar'].lineno}"



def test_symbols_java():
    """Java types and methods land in the index (#98)."""
    from peek.scanner import scan
    from peek.symbols import index_symbols
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "a.java").write_text(
            "package com.example;\n"
            "\n"
            "import java.util.List;\n"
            "\n"
            "public class Foo {\n"
            "    private final int port;\n"
            "\n"
            "    public Foo(int port) {\n"
            "        this.port = port;\n"
            "    }\n"
            "\n"
            "    public static void main(String[] args) {\n"
            "    }\n"
            "\n"
            "    private List<String> names() {\n"
            "        return null;\n"
            "    }\n"
            "}\n"
            "\n"
            "interface Handler {\n"
            "}\n"
            "\n"
            "enum State {\n"
            "    IDLE\n"
            "}\n"
            "\n"
            "record Point(int x, int y) {\n"
            "}\n"
        )
        sr = scan(p)
        syms = index_symbols(sr)
        found = {(s.name, s.kind) for s in syms}

        # The acceptance criterion: `class Foo` is indexed.
        assert ("Foo", "class") in found
        # A plain (modifier-less) declaration still counts as a type.
        for name in ("Handler", "State", "Point"):
            assert (name, "class") in found, name
        # Static method, and a method with a generic return type.
        for name in ("main", "names"):
            assert (name, "def") in found, name
        # The constructor shares the class's name, so `Foo` is both -- two
        # different places to jump to, not a duplicate entry.
        assert ("Foo", "def") in found
        assert all(s.file.name == "a.java" for s in syms)


def test_symbols_java_ignores_control_flow_and_calls():
    """A modifier is required, which is what keeps `if (` and `foo(` out."""
    from peek.scanner import scan
    from peek.symbols import index_symbols
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "a.java").write_text(
            "public class Only {\n"
            "    public void run(int n) {\n"
            "        if (n > 0) {\n"
            "            while (n-- > 0) {\n"
            "                System.out.println(n);\n"
            "            }\n"
            "        }\n"
            "        switch (n) {\n"
            "            default:\n"
            "                break;\n"
            "        }\n"
            "        helper(n);\n"
            "        return;\n"
            "    }\n"
            "}\n"
        )
        names = {s.name for s in index_symbols(scan(p))}

        assert names == {"Only", "run"}


def test_symbols_java_lineno_is_the_declaration_line():
    from peek.scanner import scan
    from peek.symbols import index_symbols
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)
        (p / "a.java").write_text(
            "package com.example;\n"   # 1
            "\n"                       # 2
            "public class Foo {\n"     # 3
            "\n"                       # 4
            "    public void bar() {\n"  # 5
            "    }\n"
            "}\n"
        )
        by_name = {s.name: s for s in index_symbols(scan(p))}

        assert by_name["Foo"].lineno == 3
        assert by_name["bar"].lineno == 5
