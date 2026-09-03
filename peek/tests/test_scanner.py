"""Tests for scanner — edge cases, .gitignore, binary, empty, huge."""

import tempfile
from pathlib import Path

from peek.scanner import scan, detect_tech_stack, detect_entry_points


def _write(p: Path, content: str | bytes):
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        p.write_bytes(content)
    else:
        p.write_text(content, encoding="utf-8")


def test_scan_empty():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        sr = scan(root)
        assert sr.total_files == 0
        assert sr.stats["total_loc"] == 0


def test_scan_ignores_git_and_venv():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # Should be ignored
        _write(root / ".git" / "config", "git")
        _write(root / ".venv" / "lib.py", "x=1")
        _write(root / "__pycache__" / "a.pyc", b"\x00\x01")
        _write(root / "real.py", "x=1\n")
        sr = scan(root)
        rels = {f.rel.as_posix() for f in sr.files}
        assert "real.py" in rels
        assert not any("__pycache__" in r for r in rels)
        assert not any(".git" in r for r in rels)
        assert not any(".venv" in r for r in rels)


def test_scan_gitignore():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root / ".gitignore", "*.pyc\nignored/\n")
        _write(root / "a.py", "x=1")
        _write(root / "b.pyc", b"\x00")
        _write(root / "ignored" / "c.py", "y=1")
        sr = scan(root)
        rels = {f.rel.as_posix() for f in sr.files}
        assert "a.py" in rels
        assert "b.pyc" not in rels
        assert "ignored/c.py" not in rels


def test_nested_gitignore():
    """A `.gitignore` in a subdirectory applies to that subtree (#102).

    `git check-ignore` honours a nested `.gitignore`; a scanner that reads
    only the root one silently indexes files the repository considers
    ignored. The scanner layers per-directory specs as it walks -- this pins
    that behaviour, which nothing else covered.
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root / ".gitignore", "*.pyc\n")
        _write(root / "src" / "foo" / ".gitignore", "*.log\nbuild/\n")
        _write(root / "src" / "foo" / "bar.py", "x=1")
        _write(root / "src" / "foo" / "debug.log", "noise")
        _write(root / "src" / "foo" / "build" / "out.py", "z=3")
        # A sibling subtree the nested rule must NOT reach.
        _write(root / "src" / "other" / "keep.log", "kept")
        # And the root rule must still apply inside the nested subtree.
        _write(root / "src" / "foo" / "stale.pyc", b"\x00")

        rels = {f.rel.as_posix() for f in scan(root).files}

        assert "src/foo/bar.py" in rels
        assert "src/foo/debug.log" not in rels, "nested .gitignore was ignored"
        assert "src/foo/build/out.py" not in rels, "nested directory rule was ignored"
        assert "src/foo/stale.pyc" not in rels, "root rule stopped applying in a subtree"
        assert "src/other/keep.log" in rels, "nested rule leaked into a sibling subtree"


def test_scan_binary_and_huge():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # Binary with null byte
        _write(root / "binary.bin", b"\x00\xff\x00hello")
        # Huge file >1MB
        _write(root / "huge.py", "a=1\n" * 300000)  # ~1.2MB
        _write(root / "small.py", "x=1\n")
        sr = scan(root)
        rels = {f.rel.as_posix() for f in sr.files}
        # binary and huge still present but loc 0 or approximated
        assert "small.py" in rels
        # loc for huge should be approximated (non-zero) but not crash
        huge = next(f for f in sr.files if f.rel.name == "huge.py")
        assert huge.loc >= 0
        # binary loc 0
        binf = next(f for f in sr.files if f.rel.name == "binary.bin")
        assert binf.loc == 0


def test_scan_symlink_inside():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root / "a.py", "x=1")
        # Symlink inside root
        try:
            (root / "link.py").symlink_to(root / "a.py")
            sr = scan(root)
            # Should not crash, may count link or skip — either is fine but not crash
            assert sr.total_files >= 1
        except OSError:
            # Symlinks not supported on this platform
            pass


def test_scan_max_files():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for i in range(25):
            _write(root / f"f{i}.py", "x=1\n")
        sr = scan(root, max_files=10)
        assert sr.total_files == 10
        assert sr.stats["truncated"] is True


def test_tech_stack_and_entry():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root / "pyproject.toml", '[project]\nname="t"\ndependencies=["fastapi","typer"]\n[project.scripts]\ncli="pkg.cli:app"\n')
        _write(root / "pkg" / "cli.py", 'import typer\ndef main(): pass\nif __name__ == "__main__": main()\n')
        _write(root / "pkg" / "utils.py", "x=1")
        sr = scan(root)
        assert "FastAPI" in sr.tech_stack.get("frameworks", []) or "Typer" in sr.tech_stack.get("frameworks", [])
        # entry should be cli.py via pyproject.scripts
        entry_names = [p.name for p in sr.entry_candidates]
        assert "cli.py" in entry_names


def test_scan_never_crashes_on_weird():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root / "broken.py", "def broken(:")
        _write(root / "empty.py", "")
        sr = scan(root)
        # Should not raise, and should handle broken file gracefully
        assert sr.total_files >= 2


def test_symlink_loop():
    """Symlink file and dir loops must not hang or double-count (#103)."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root / "a.py", "x=1\n")
        _write(root / "sub" / "c.py", "y=1\n")
        try:
            # File symlink: b.py -> a.py (same inode, should not double-count)
            (root / "b.py").symlink_to(root / "a.py")
            # Dir symlink loop: sub/loop -> root (must not be followed)
            (root / "sub" / "loop").symlink_to(root)
            # Additional file symlink loop: a symlink cycle
            # Create d.py symlink -> e.py and e.py symlink -> d.py is not possible
            # because d.py doesn't exist yet. Instead test broken/circular via dir.
        except (OSError, NotImplementedError):
            # Symlinks not supported on this platform / privilege
            return
        sr = scan(root)
        # Should complete without hanging; file symlink deduped, dir loop not followed
        rels = {f.rel.as_posix() for f in sr.files}
        # Real files must be present
        assert "a.py" in rels
        assert "sub/c.py" in rels
        # Should not double-count a.py via b.py
        # b.py shares inode with a.py, so total distinct files == 2
        # Allow either 2 (skip symlink) or 2 with dedup; never 3+ and never infinite
        assert sr.total_files == 2
        # Ensure loop dir not traversed infinitely — file count stays bounded
        assert not any("loop" in r for r in rels)
