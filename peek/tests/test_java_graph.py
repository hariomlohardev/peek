"""Java files in the import graph: `import` statements and same-package use."""

from pathlib import Path

from typer.testing import CliRunner

from peek.analyzer import analyze
from peek.cli import app
from peek.scanner import scan


def _repo(root: Path, files: dict[str, str]) -> Path:
    for name, body in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return root


def _edges(root: Path) -> dict[str, list[str]]:
    """The graph as file names, for Java files only."""
    ar = analyze(scan(root))
    return {
        src.name: sorted(dst.name for dst in dsts)
        for src, dsts in ar.graph.items()
        if src.suffix == ".java"
    }


def test_imports_resolve_by_fully_qualified_name(tmp_path):
    root = _repo(
        tmp_path,
        {
            "src/main/java/com/acme/App.java": (
                "package com.acme;\n\n"
                "import com.acme.model.User;\n"
                "import com.acme.util.Strings;\n"
                "import java.util.List;\n"
                "import org.slf4j.Logger;\n\n"
                "public class App {}\n"
            ),
            "src/main/java/com/acme/model/User.java": "package com.acme.model;\n\npublic class User {}\n",
            "src/main/java/com/acme/util/Strings.java": "package com.acme.util;\n\npublic class Strings {}\n",
        },
    )

    edges = _edges(root)

    assert edges["App.java"] == ["Strings.java", "User.java"]
    assert edges["User.java"] == []


def test_nested_class_and_static_imports_point_at_the_outer_class(tmp_path):
    root = _repo(
        tmp_path,
        {
            "a/Main.java": (
                "package a;\n"
                "import b.Outer.Inner;\n"
                "import static b.Util.join;\n"
                "import static b.Consts.*;\n"
                "class Main {}\n"
            ),
            "b/Outer.java": "package b;\npublic class Outer { public static class Inner {} }\n",
            "b/Util.java": "package b;\npublic class Util {}\n",
            "b/Consts.java": "package b;\npublic class Consts {}\n",
            "b/Unused.java": "package b;\npublic class Unused {}\n",
        },
    )

    assert _edges(root)["Main.java"] == ["Consts.java", "Outer.java", "Util.java"]


def test_wildcard_import_links_only_the_classes_the_file_names(tmp_path):
    root = _repo(
        tmp_path,
        {
            "a/Main.java": "package a;\nimport b.*;\nclass Main { Used field; }\n",
            "b/Used.java": "package b;\npublic class Used {}\n",
            "b/Unused.java": "package b;\npublic class Unused {}\n",
        },
    )

    assert _edges(root)["Main.java"] == ["Used.java"]


def test_same_package_classes_are_linked_without_an_import(tmp_path):
    root = _repo(
        tmp_path,
        {
            "shop/Cart.java": "package shop;\nclass Cart { Item first; }\n",
            "shop/Item.java": "package shop;\nclass Item {}\n",
            "shop/Order.java": "package shop;\n// an Item is not used here, only mentioned\n/* Cart neither */\nclass Order {}\n",
            "other/Item.java": "package other;\nclass Item {}\n",
        },
    )

    ar = analyze(scan(root))
    by_rel = {
        p.relative_to(ar.root).as_posix(): sorted(d.relative_to(ar.root).as_posix() for d in dsts)
        for p, dsts in ar.graph.items()
    }

    assert by_rel["shop/Cart.java"] == ["shop/Item.java"]  # not other/Item.java
    assert by_rel["shop/Order.java"] == []  # names in comments do not count


def test_layout_does_not_matter_and_the_default_package_works(tmp_path):
    root = _repo(
        tmp_path,
        {
            "Main.java": "class Main { Helper h; }\n",
            "Helper.java": "class Helper {}\n",
            "flat/Api.java": "package deep.pkg.api;\nimport deep.pkg.impl.Impl;\nclass Api {}\n",
            "elsewhere/Impl.java": "package deep.pkg.impl;\nclass Impl {}\n",
        },
    )

    edges = _edges(root)

    assert edges["Main.java"] == ["Helper.java"]
    assert edges["Api.java"] == ["Impl.java"]


def test_commented_imports_and_malformed_files_add_no_edges(tmp_path):
    root = _repo(
        tmp_path,
        {
            "a/Main.java": (
                "package a;\n"
                "// import b.Gone;\n"
                "/* import b.Gone; */\n"
                "import ;\nimport b.;\nimport b.Missing;\n"
                "class Main {}\n"
            ),
            "b/Gone.java": "package b;\nclass Gone {}\n",
            "b/Empty.java": "",
        },
    )
    (root / "b" / "Odd.java").write_bytes(b"\xff\xfe package b; \x80 class Odd {}")

    assert _edges(root)["Main.java"] == []


def test_java_files_are_ranked_and_most_imported_comes_first(tmp_path):
    root = _repo(
        tmp_path,
        {
            "app/A.java": "package app;\nimport core.Shared;\nclass A {}\n",
            "app/B.java": "package app;\nimport core.Shared;\nclass B {}\n",
            "app/C.java": "package app;\nimport core.Shared;\nclass C {}\n",
            "core/Shared.java": "package core;\npublic class Shared {}\n",
        },
    )

    ar = analyze(scan(root))

    assert ar.stats["graph_nodes"] == 4
    assert ar.stats["graph_edges"] == 3
    assert ar.ranked[0].rel.as_posix() == "core/Shared.java"


def test_cli_graph_shows_java_edges(tmp_path):
    root = _repo(
        tmp_path,
        {
            "a/Main.java": "package a;\nimport b.Lib;\nclass Main {}\n",
            "b/Lib.java": "package b;\npublic class Lib {}\n",
        },
    )

    r = CliRunner().invoke(app, ["graph", str(root), "--format", "dot"])

    assert r.exit_code == 0, r.output
    assert '"a/Main.java" -> "b/Lib.java";' in r.output
