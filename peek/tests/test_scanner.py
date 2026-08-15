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


def test_nested_gitignore():
    """A .gitignore in a subdirectory applies to that subtree.

    git reads a .gitignore in every directory it walks, matching its patterns
    relative to that directory. peek used to read only the root one, so
    `src/foo/.gitignore` was silently ignored.
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root / "keep.py", "x = 1\n")
        _write(root / "src" / "foo" / ".gitignore", "*.log\ngenerated/\n")
        _write(root / "src" / "foo" / "bar.py", "y = 2\n")
        _write(root / "src" / "foo" / "debug.log", "noise\n")
        _write(root / "src" / "foo" / "generated" / "out.py", "z = 3\n")

        rels = {f.rel.as_posix() for f in scan(root).files}

        assert "keep.py" in rels
        assert "src/foo/bar.py" in rels
        assert "src/foo/debug.log" not in rels, "nested .gitignore pattern was not applied"
        assert "src/foo/generated/out.py" not in rels, "nested ignored directory was descended into"


def test_nested_gitignore_is_scoped_to_its_own_directory():
    """The control: a nested pattern must not leak upwards or sideways.

    Without this, an implementation that dumped nested patterns into the root
    spec would pass the test above while quietly hiding unrelated files.
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root / "src" / "foo" / ".gitignore", "*.log\n")
        _write(root / "src" / "foo" / "inside.log", "hidden\n")
        _write(root / "src" / "other" / "outside.log", "visible\n")
        _write(root / "toplevel.log", "visible\n")

        rels = {f.rel.as_posix() for f in scan(root).files}

        assert "src/foo/inside.log" not in rels
        assert "src/other/outside.log" in rels, "nested pattern leaked to a sibling directory"
        assert "toplevel.log" in rels, "nested pattern leaked to the repo root"


def test_root_gitignore_still_applies_to_subdirectories():
    """Root patterns keep working — nested handling must not replace them."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root / ".gitignore", "*.log\n")
        _write(root / "src" / "deep" / "a.log", "noise\n")
        _write(root / "src" / "deep" / "a.py", "x = 1\n")

        rels = {f.rel.as_posix() for f in scan(root).files}

        assert "src/deep/a.log" not in rels
        assert "src/deep/a.py" in rels
