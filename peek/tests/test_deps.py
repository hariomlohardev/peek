"""`peek deps --why <package>` — tracing a dependency back to the code (#32)."""

import pathlib
import tempfile

from typer.testing import CliRunner

from peek.analyzer import analyze
from peek.cli import app
from peek.deps import direct_importers, render, why
from peek.scanner import scan

runner = CliRunner()


def _repo(files: dict[str, str]) -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp())
    for name, body in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return root


def test_traces_the_chain_from_an_entry_point_to_the_package():
    root = _repo({"a.py": "import b\n", "b.py": "import rich\n"})

    chains = why(scan(root), analyze(scan(root)), "rich")

    assert len(chains) == 1
    assert [f.name for f in chains[0].files] == ["a.py", "b.py"]
    assert chains[0].lineno == 1


def test_a_submodule_import_counts_as_the_package():
    """`from rich.console import Console` is a use of `rich`.

    The top-level name is what appears in a lockfile, and what someone asking
    this question types.
    """
    root = _repo({"b.py": "from rich.console import Console\n"})

    assert direct_importers(scan(root), "rich")


def test_a_package_nobody_imports_says_so_rather_than_failing():
    root = _repo({"a.py": "import b\n", "b.py": "x = 1\n"})

    assert why(scan(root), analyze(scan(root)), "rich") == []
    assert "Nothing imports" in render([], "rich", root)[0]


def test_a_similarly_named_package_is_not_matched():
    """`rich` must not be answered by an import of `richtext`."""
    root = _repo({"b.py": "import richtext\n"})

    assert direct_importers(scan(root), "rich") == {}


def test_a_relative_import_is_never_a_package():
    root = _repo({"pkg/__init__.py": "", "pkg/b.py": "from . import sibling\n"})

    assert direct_importers(scan(root), ".") == {}


def test_an_import_cycle_produces_a_short_answer_not_no_answer():
    """A cycle is common; it must not hang or return nothing."""
    root = _repo({
        "a.py": "import b\nimport rich\n",
        "b.py": "import a\n",
    })

    chains = why(scan(root), analyze(scan(root)), "rich")

    assert chains
    assert chains[0].files[-1].name == "a.py"


def test_the_shortest_explanation_comes_first():
    root = _repo({
        "deep1.py": "import deep2\n",
        "deep2.py": "import deep3\n",
        "deep3.py": "import rich\n",
        "shallow.py": "import rich\n",
    })

    chains = why(scan(root), analyze(scan(root)), "rich")

    assert chains[0].files[-1].name == "shallow.py", [f.name for c in chains for f in c.files]


def test_cli_reports_the_chain():
    root = _repo({"a.py": "import b\n", "b.py": "import rich\n"})

    result = runner.invoke(app, ["deps", str(root), "--why", "rich"])

    assert result.exit_code == 0
    assert "rich" in result.output
    assert "b.py" in result.output


def test_cli_without_a_package_explains_what_to_type():
    result = runner.invoke(app, ["deps", "."])

    assert result.exit_code == 2
    assert "--why" in result.output


def test_cli_json_output_is_valid_json():
    import json

    root = _repo({"a.py": "import b\n", "b.py": "import rich\n"})

    result = runner.invoke(app, ["deps", str(root), "--why", "rich", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["package"] == "rich"
    assert len(payload["chains"]) == 1
