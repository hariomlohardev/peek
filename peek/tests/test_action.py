"""Issues #30 (peek-action) + #81 (README GitHub Action example)."""

import json
import pathlib

from typer.testing import CliRunner

from peek.cli import app

ROOT = pathlib.Path(__file__).resolve().parents[2]
runner = CliRunner()


def test_action_yml_runs_analyze_json():
    action = (ROOT / "action.yml").read_text(encoding="utf-8")
    assert 'using: "composite"' in action
    assert "peek analyze" in action and "--json" in action
    assert "start_here" in action and "summary" in action
    assert "pip install peek-code" in action


def test_peek_example_workflow_posts_comment():
    workflow = (ROOT / ".github" / "workflows" / "peek.yml").read_text(encoding="utf-8")
    assert "actions/github-script" in workflow
    assert "hariomlohardev/peek@v1" in workflow
    assert "start_here" in workflow or "start-here" in workflow


def test_action_parse_matches_analyze_json(tmp_path):
    """The action.yml parser must work on real `peek analyze --json` output."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("import b\nx = 1\n", encoding="utf-8")
    (repo / "b.py").write_text("y = 2\n", encoding="utf-8")
    r = runner.invoke(app, ["analyze", str(repo), "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    ranked = data.get("ranked", [])[:5]
    start_here = "\n".join(
        f"{i + 1}. {item.get('rel', item.get('path', '?'))} ({item.get('score', 0):.1f})"
        for i, item in enumerate(ranked)
    )
    assert start_here.strip(), "action would post an empty Start Here"
    assert data.get("summary"), "action needs a summary"
    assert "a.py" in start_here or "b.py" in start_here


def test_docs_has_github_action_section():
    docs = (ROOT / "docs.md").read_text(encoding="utf-8")
    assert "GitHub Action" in docs
    assert "hariomlohardev/peek@v1" in docs


def test_readmes_have_github_action_section():
    for readme in (ROOT / "README.md", ROOT / "peek" / "README.md"):
        text = readme.read_text(encoding="utf-8")
        assert "GitHub Action" in text, readme
        assert "hariomlohardev/peek@v1" in text, readme
