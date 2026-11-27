"""`peek cycles` -- finding import cycles in the analyzer's graph."""

import json
import re
from pathlib import Path

from typer.testing import CliRunner

from peek.analyzer import analyze
from peek.cli import app
from peek.cycles import find_cycles, render
from peek.scanner import scan

runner = CliRunner()

ROOT = Path("/repo")


def _graph(edges: dict[str, list[str]]) -> dict[Path, set[Path]]:
    graph: dict[Path, set[Path]] = {}
    for src, dsts in edges.items():
        graph.setdefault(ROOT / src, set()).update(ROOT / d for d in dsts)
        for dst in dsts:
            graph.setdefault(ROOT / dst, set())
    return graph


def _names(paths: list[Path]) -> list[str]:
    return [p.relative_to(ROOT).as_posix() for p in paths]


def _repo(root: Path, files: dict[str, str]) -> Path:
    for name, body in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return root


def test_no_cycle_in_a_tree_or_an_empty_graph():
    assert find_cycles({}) == []
    assert find_cycles(_graph({"a.py": ["b.py", "c.py"], "b.py": ["c.py"]})) == []


def test_two_file_cycle():
    cycles = find_cycles(_graph({"a.py": ["b.py"], "b.py": ["a.py"], "c.py": ["a.py"]}))

    assert len(cycles) == 1
    assert _names(cycles[0].files) == ["a.py", "b.py"]
    assert _names(cycles[0].loop) == ["a.py", "b.py", "a.py"]


def test_separate_cycles_are_reported_separately_smallest_first():
    cycles = find_cycles(
        _graph(
            {
                "x.py": ["y.py"],
                "y.py": ["z.py"],
                "z.py": ["x.py"],
                "m.py": ["n.py"],
                "n.py": ["m.py"],
            }
        )
    )

    assert [_names(c.files) for c in cycles] == [["m.py", "n.py"], ["x.py", "y.py", "z.py"]]
    assert _names(cycles[1].loop) == ["x.py", "y.py", "z.py", "x.py"]


def test_overlapping_loops_form_one_group_with_a_shortest_loop_as_example():
    cycles = find_cycles(
        _graph(
            {
                "a.py": ["b.py"],
                "b.py": ["c.py", "a.py"],
                "c.py": ["d.py"],
                "d.py": ["a.py"],
            }
        )
    )

    assert len(cycles) == 1
    assert _names(cycles[0].files) == ["a.py", "b.py", "c.py", "d.py"]
    assert _names(cycles[0].loop) == ["a.py", "b.py", "a.py"]
    assert render(cycles, ROOT) == [
        "1 import cycle:",
        "1. a.py -> b.py -> a.py  (+2 more in this group)",
    ]


def test_result_does_not_depend_on_insertion_order():
    edges = {"b.py": ["c.py"], "c.py": ["a.py"], "a.py": ["b.py"]}
    forward = find_cycles(_graph(edges))
    backward = find_cycles(_graph(dict(reversed(list(edges.items())))))

    assert _names(forward[0].loop) == _names(backward[0].loop) == ["a.py", "b.py", "c.py", "a.py"]


def test_a_long_chain_does_not_hit_the_recursion_limit():
    edges = {f"m{i:05d}.py": [f"m{i + 1:05d}.py"] for i in range(5000)}
    assert find_cycles(_graph(edges)) == []

    edges["m05000.py"] = ["m00000.py"]
    cycles = find_cycles(_graph(edges))
    assert len(cycles) == 1
    assert len(cycles[0].files) == 5001


def test_importing_the_containing_package_is_not_a_cycle():
    """`pkg/__init__.py` re-exporting from a submodule that imports `pkg` is ordinary."""
    graph = _graph(
        {
            "pkg/__init__.py": ["pkg/a.py", "pkg/sub/__init__.py"],
            "pkg/a.py": ["pkg/__init__.py"],
            "pkg/sub/__init__.py": ["pkg/sub/b.py"],
            "pkg/sub/b.py": ["pkg/sub/__init__.py", "pkg/__init__.py"],
            # Rust: the same shape with mod.rs, lib.rs and a 2018-style a.rs + a/.
            "src/lib.rs": ["src/net/mod.rs", "src/db.rs"],
            "src/net/mod.rs": ["src/net/tcp.rs", "src/lib.rs"],
            "src/net/tcp.rs": ["src/net/mod.rs", "src/lib.rs"],
            "src/db.rs": ["src/db/pool.rs"],
            "src/db/pool.rs": ["src/db.rs"],
        }
    )

    assert find_cycles(graph) == []


def test_a_cycle_through_another_package_is_still_reported():
    graph = _graph(
        {
            "a/__init__.py": ["a/x.py"],
            "a/x.py": ["b/__init__.py"],
            "b/__init__.py": ["b/y.py"],
            "b/y.py": ["a/x.py"],
        }
    )

    cycles = find_cycles(graph)

    assert [_names(c.files) for c in cycles] == [["a/x.py", "b/__init__.py", "b/y.py"]]


def test_render_limits_the_list_and_says_so():
    edges: dict[str, list[str]] = {}
    for i in range(5):
        edges[f"a{i}.py"] = [f"b{i}.py"]
        edges[f"b{i}.py"] = [f"a{i}.py"]

    lines = render(find_cycles(_graph(edges)), ROOT, limit=2)

    assert lines[0] == "5 import cycles:"
    assert lines[1:3] == ["1. a0.py -> b0.py -> a0.py", "2. a1.py -> b1.py -> a1.py"]
    assert lines[3].startswith("... and 3 more")
    assert render([], ROOT) == ["No import cycles."]


def test_finds_a_real_python_cycle_including_a_lazy_import(tmp_path):
    root = _repo(
        tmp_path,
        {
            "app/__init__.py": "",
            "app/models.py": "from app import db\n",
            "app/db.py": "def session():\n    from app.models import User\n    return User\n",
            "app/util.py": "import os\n",
        },
    )

    ar = analyze(scan(root))
    cycles = find_cycles(ar.graph)

    assert [[p.relative_to(ar.root).as_posix() for p in c.files] for c in cycles] == [
        ["app/db.py", "app/models.py"]
    ]


def test_cli_lists_cycles_and_exits_zero_by_default(tmp_path):
    root = _repo(tmp_path, {"a.py": "import b\n", "b.py": "import a\n", "c.py": "import a\n"})

    r = runner.invoke(app, ["cycles", str(root)])

    assert r.exit_code == 0, r.output
    assert "1 import cycle:" in r.output
    assert "1. a.py -> b.py -> a.py" in r.output


def test_cli_fail_flag_exits_one_only_when_a_cycle_exists(tmp_path):
    tangled = _repo(tmp_path / "tangled", {"a.py": "import b\n", "b.py": "import a\n"})
    clean = _repo(tmp_path / "clean", {"a.py": "import b\n", "b.py": "x = 1\n"})

    assert runner.invoke(app, ["cycles", str(tangled), "--fail"]).exit_code == 1
    clean_run = runner.invoke(app, ["cycles", str(clean), "--fail"])
    assert clean_run.exit_code == 0
    assert "No import cycles." in clean_run.output


def test_cli_json_output(tmp_path):
    root = _repo(tmp_path, {"pkg/a.py": "import pkg.b\n", "pkg/b.py": "import pkg.a\n"})

    r = runner.invoke(app, ["cycles", str(root), "--json"])

    assert r.exit_code == 0, r.output
    payload = json.loads(r.output)
    assert payload["count"] == 1
    assert payload["cycles"] == [
        {"files": ["pkg/a.py", "pkg/b.py"], "loop": ["pkg/a.py", "pkg/b.py", "pkg/a.py"]}
    ]


def test_cli_help_is_routed_to_the_command():
    r = runner.invoke(app, ["cycles", "--help"])

    assert r.exit_code == 0, r.output
    # Some CI environments force colour in help output.
    assert "peek cycles src/ --fail" in re.sub(r"\x1b\[[0-9;]*m", "", r.output)
