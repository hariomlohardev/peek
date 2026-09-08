"""Issue #79 — peek as a pre-commit hook (no extra deps: plain-text checks)."""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_pre_commit_hooks_yaml_valid():
    hooks_file = ROOT / ".pre-commit-hooks.yaml"
    assert hooks_file.exists(), "repo must ship .pre-commit-hooks.yaml"
    text = hooks_file.read_text(encoding="utf-8")
    assert "- id: peek-map" in text, "must define a peek-map hook"
    assert "peek --no-tui" in text, "hook entry must run peek --no-tui"


def test_docs_mentions_pre_commit():
    docs = (ROOT / "docs.md").read_text(encoding="utf-8")
    assert "pre-commit" in docs.lower()
    assert "peek-map" in docs
