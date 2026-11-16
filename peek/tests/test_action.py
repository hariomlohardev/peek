"""Issues #30 (peek-action) + #81 (README GitHub Action example)."""

import json
import os
import pathlib
import shutil
import subprocess
import textwrap

import pytest
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
    assert "PEEK_SUMMARY: ${{ steps.peek.outputs.summary }}" in workflow
    assert "PEEK_START_HERE: ${{ steps.peek.outputs.start_here }}" in workflow
    assert "if: github.event.pull_request.head.repo.full_name == github.repository" in workflow


@pytest.mark.parametrize(
    "summary,start_here",
    [
        ("", ""),
        (
            "Uses `peek`, 'quotes', \"double quotes\", and C:\\src\\app\nSecond line",
            "1. ${process.exit(42)}\n2. `module` \\ path — 日本語",
        ),
    ],
)
def test_peek_comment_preserves_report_text(summary, start_here):
    result = _run_comment_script(summary, start_here)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "owner": "example",
        "repo": "repo",
        "issue_number": 183,
        "body": f"## peek map\n{summary}\n\n**Start Here**\n{start_here}",
    }


def test_peek_comment_propagates_api_failure():
    result = _run_comment_script("summary", "start here", fail=True)
    assert result.returncode != 0
    assert "comment API failed" in result.stderr


def _run_comment_script(summary, start_here, *, fail=False):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is needed to execute the github-script regression check")
    workflow = (ROOT / ".github" / "workflows" / "peek.yml").read_text(encoding="utf-8")
    script = textwrap.dedent(workflow.split("script: |\n", 1)[1])
    # Model Actions' expression substitution to reproduce the original bug too.
    script = script.replace("${{ steps.peek.outputs.summary }}", summary)
    script = script.replace("${{ steps.peek.outputs.start_here }}", start_here)
    harness = """
const context = {repo: {owner: 'example', repo: 'repo'}, issue: {number: 183}};
const github = {rest: {issues: {createComment: async (comment) => {
  if (process.env.FAIL_COMMENT === '1') throw new Error('comment API failed');
  console.log(JSON.stringify(comment));
}}}};
"""
    return subprocess.run(
        [node, "--input-type=module", "-e", harness + script],
        env={
            **os.environ,
            "PEEK_SUMMARY": summary,
            "PEEK_START_HERE": start_here,
            "FAIL_COMMENT": "1" if fail else "0",
        },
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


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
