"""Rust files in the import graph: `mod` declarations and `use` paths."""

from pathlib import Path, PureWindowsPath

from typer.testing import CliRunner

from peek._rust_graph import rust_targets
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
    """The graph as relative posix paths, for Rust files only."""
    ar = analyze(scan(root))
    return {
        src.relative_to(ar.root).as_posix(): sorted(
            dst.relative_to(ar.root).as_posix() for dst in dsts
        )
        for src, dsts in ar.graph.items()
        if src.suffix == ".rs"
    }


def test_mod_declarations_point_at_the_module_file(tmp_path):
    root = _repo(
        tmp_path,
        {
            "src/lib.rs": "mod config;\npub mod net;\npub(crate) mod db;\n",
            "src/config.rs": "pub struct Config;\n",
            "src/net/mod.rs": "mod tcp;\n",
            "src/net/tcp.rs": "pub struct Conn;\n",
            "src/db.rs": "mod pool;\n",
            "src/db/pool.rs": "pub struct Pool;\n",
        },
    )

    edges = _edges(root)

    assert edges["src/lib.rs"] == ["src/config.rs", "src/db.rs", "src/net/mod.rs"]
    assert edges["src/net/mod.rs"] == ["src/net/tcp.rs"]  # mod.rs keeps children beside it
    assert edges["src/db.rs"] == ["src/db/pool.rs"]  # db.rs keeps children in db/
    assert edges["src/config.rs"] == []


def test_use_paths_resolve_to_the_deepest_module_file(tmp_path):
    root = _repo(
        tmp_path,
        {
            "src/main.rs": "mod config;\nmod net;\nuse crate::net::tcp::Conn;\nfn main() {}\n",
            "src/config.rs": "pub struct Config;\npub const PORT: u16 = 1;\n",
            "src/net/mod.rs": "pub mod tcp;\npub mod udp;\n",
            "src/net/tcp.rs": "use crate::config::{Config, PORT as P};\nuse super::udp::Socket;\npub struct Conn;\n",
            "src/net/udp.rs": "use crate::Config;\nuse super::super::config;\npub struct Socket;\n",
        },
    )

    edges = _edges(root)

    assert edges["src/main.rs"] == ["src/config.rs", "src/net/mod.rs", "src/net/tcp.rs"]
    assert edges["src/net/tcp.rs"] == ["src/config.rs", "src/net/udp.rs"]
    # `crate::Config` names an item of the crate root; `super::super::config` is a file.
    assert edges["src/net/udp.rs"] == ["src/config.rs", "src/main.rs"]


def test_nested_use_groups_self_and_child_modules(tmp_path):
    root = _repo(
        tmp_path,
        {
            "src/lib.rs": ("mod a;\nmod b;\nuse crate::{a::{one::One, two}, b::*};\nuse a::one;\n"),
            "src/a/mod.rs": "pub mod one;\npub mod two;\nuse self::one::One;\n",
            "src/a/one.rs": "pub struct One;\n",
            "src/a/two.rs": "pub struct Two;\n",
            "src/b.rs": "pub struct B;\n",
        },
    )

    edges = _edges(root)

    assert edges["src/lib.rs"] == ["src/a/mod.rs", "src/a/one.rs", "src/a/two.rs", "src/b.rs"]
    assert edges["src/a/mod.rs"] == ["src/a/one.rs", "src/a/two.rs"]


def test_workspace_crates_are_linked_by_cargo_package_name(tmp_path):
    root = _repo(
        tmp_path,
        {
            "Cargo.toml": '[workspace]\nmembers = ["crates/*"]\n',
            "crates/core/Cargo.toml": '[package]\nname = "my-core"\nversion = "0.1.0"\n',
            "crates/core/src/lib.rs": "pub mod util;\npub struct Thing;\n",
            "crates/core/src/util.rs": "pub fn helper() {}\n",
            "crates/app/Cargo.toml": '[package]\nname = "app"\nversion = "0.1.0"\n',
            "crates/app/src/main.rs": "use my_core::util::helper;\nuse my_core::Thing;\nfn main() {}\n",
        },
    )

    edges = _edges(root)

    assert edges["crates/app/src/main.rs"] == ["crates/core/src/lib.rs", "crates/core/src/util.rs"]


def test_external_crates_inline_modules_and_comments_add_no_edges(tmp_path):
    root = _repo(
        tmp_path,
        {
            "src/lib.rs": (
                "use std::collections::HashMap;\n"
                "use serde::{Deserialize, Serialize};\n"
                "use ::tokio::runtime::Runtime;\n"
                "// mod gone;\n"
                "// use crate::other::Thing;\n"
                "mod tests {\n    use super::*;\n}\n"
                "mod missing;\n"
            ),
            "src/other.rs": "pub struct Thing;\n",
            "src/tests.rs": "",
        },
    )

    assert _edges(root)["src/lib.rs"] == []


def test_use_inside_an_inline_module_is_one_module_deeper(tmp_path):
    """`use super::*` in `mod tests { }` means this file, not the parent module."""
    root = _repo(
        tmp_path,
        {
            "src/lib.rs": "mod a;\nmod b;\nmod helper;\n",
            "src/a.rs": (
                "pub fn helper() {}\n"
                "mod child;\n"
                "#[cfg(test)]\n"
                "mod tests {\n"
                "    use super::*;\n"
                "    use super::helper;\n"
                "    use super::child::Kid;\n"
                "    use super::super::b::thing;\n"
                "    use self::local::Thing;\n"
                "    mod local {\n"
                "        use super::super::helper;\n"
                "    }\n"
                "}\n"
                "use self::child::Kid;\n"
            ),
            "src/a/child.rs": "pub struct Kid;\n",
            "src/b.rs": "pub fn thing() {}\n",
            "src/helper.rs": "pub fn unrelated() {}\n",
        },
    )

    edges = _edges(root)

    # No edge to lib.rs or helper.rs: `super::helper` is the function in a.rs itself.
    assert edges["src/a.rs"] == ["src/a/child.rs", "src/b.rs"]


def test_path_attribute_and_integration_test_modules(tmp_path):
    root = _repo(
        tmp_path,
        {
            "src/lib.rs": "pub fn run() {}\n",
            "tests/common/mod.rs": "pub fn setup() {}\n",
            "tests/api.rs": "mod common;\n",
            "tests/cli.rs": '#[path = "common/mod.rs"]\nmod shared;\n',
            "benches/speed.rs": '#[path = "../tests/common/mod.rs"]\nmod common;\n',
        },
    )

    edges = _edges(root)

    assert edges["tests/api.rs"] == ["tests/common/mod.rs"]
    assert edges["tests/cli.rs"] == ["tests/common/mod.rs"]
    assert edges["benches/speed.rs"] == ["tests/common/mod.rs"]


def test_item_names_are_not_matched_to_files_case_insensitively():
    # Windows paths compare case-insensitively, so the item `crate::Config`
    # must not be taken for the module file `config.rs`.
    root = PureWindowsPath("C:/repo")
    main, config, udp = (root / "src" / n for n in ("main.rs", "config.rs", "udp.rs"))
    rust_files = {str(p): p for p in (main, config, udp)}

    targets = rust_targets(udp, "use crate::Config;\n", root, rust_files, {})

    assert [str(t) for t in targets] == [str(main)]


def test_malformed_rust_never_raises(tmp_path):
    root = _repo(
        tmp_path,
        {
            "src/lib.rs": "use crate::{a::{b, c;\nuse ;\nuse crate::;\nmod ;\nuse super::super::super::super::x;\n",
            "src/empty.rs": "",
            "src/binary.rs": "mod a;\n",
        },
    )
    (root / "src" / "odd.rs").write_bytes(b"\xff\xfe mod a; \x80\x81")

    edges = _edges(root)

    assert edges["src/lib.rs"] == []


def test_rust_files_are_ranked_and_most_imported_comes_first(tmp_path):
    root = _repo(
        tmp_path,
        {
            "src/main.rs": "mod a;\nmod b;\nmod shared;\nfn main() {}\n",
            "src/a.rs": "use crate::shared::Thing;\n",
            "src/b.rs": "use crate::shared::Thing;\n",
            "src/shared.rs": "pub struct Thing;\n",
        },
    )

    ar = analyze(scan(root))

    assert ar.stats["graph_nodes"] == 4
    assert ar.stats["graph_edges"] == 5
    assert ar.ranked[0].rel.as_posix() == "src/shared.rs"


def test_python_and_rust_share_one_graph(tmp_path):
    root = _repo(
        tmp_path,
        {
            "tool.py": "import helper\n",
            "helper.py": "x = 1\n",
            "src/lib.rs": "mod util;\n",
            "src/util.rs": "pub fn f() {}\n",
        },
    )

    ar = analyze(scan(root))
    by_rel = {
        p.relative_to(ar.root).as_posix(): {d.name for d in dsts} for p, dsts in ar.graph.items()
    }

    assert by_rel["tool.py"] == {"helper.py"}
    assert by_rel["src/lib.rs"] == {"util.rs"}


def test_cli_graph_shows_rust_edges(tmp_path):
    root = _repo(tmp_path, {"src/lib.rs": "mod util;\n", "src/util.rs": "pub fn f() {}\n"})

    r = CliRunner().invoke(app, ["graph", str(root), "--format", "dot"])

    assert r.exit_code == 0, r.output
    assert '"src/lib.rs" -> "src/util.rs";' in r.output
