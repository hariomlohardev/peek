"""Git time machine — log/diff/hot/blame via git subprocess.

No hard dep on GitPython; uses `git` binary via subprocess with graceful fallback.
Never crashes — returns empty on error (non-git dir, no git installed, bad path).
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _resolve_path(path: Path | str | None) -> Path:
    """Resolve path to directory; if file, return parent. Fallback to cwd."""
    try:
        if path is None or str(path).strip() == "":
            return Path.cwd()
        p = Path(path)
        if p.is_file():
            p = p.parent
        if not p.exists():
            # try relative to cwd
            cand = Path.cwd() / p
            if cand.exists():
                return cand
            return Path.cwd()
        return p.resolve() if p.exists() else Path.cwd()
    except Exception:
        return Path.cwd()


def _run_git(args: list[str], cwd: Path, text: bool = True, timeout: int = 5) -> str:
    try:
        out = subprocess.check_output(args, cwd=str(cwd), text=text, stderr=subprocess.DEVNULL, timeout=timeout)
        return out
    except subprocess.CalledProcessError as e:
        # e.output may contain partial
        if e.output:
            return e.output if isinstance(e.output, str) else e.output.decode("utf-8", errors="ignore")
        return ""
    except Exception:
        return ""


def git_log(path: Path | str = ".", n: int = 20, since: str | None = None, author: str | None = None, oneline: bool = True) -> str:
    """Return `git log --oneline -n` output (or --since/--author filtered).

    On non-git or error, returns "".
    """
    try:
        p = _resolve_path(path)
        try:
            n = int(n)
        except Exception:
            n = 20
        if n <= 0:
            n = 20
        cmd: list[str] = ["git", "log"]
        if oneline:
            cmd.append("--oneline")
        if since:
            cmd.extend(["--since", str(since)])
        if author:
            cmd.extend(["--author", str(author)])
        cmd.append(f"-{n}")
        return _run_git(cmd, p)
    except Exception:
        return ""


def git_diff(path: Path | str = ".", base: str = "HEAD", staged: bool = False) -> list[str]:
    """Return list of changed files (`git diff --name-only [base]` or staged).

    On error returns [].
    """
    try:
        p = _resolve_path(path)
        if staged:
            cmd = ["git", "diff", "--name-only", "--staged"]
        else:
            try:
                base_str = str(base).strip() if base is not None else "HEAD"
            except Exception:
                base_str = "HEAD"
            if base_str:
                cmd = ["git", "diff", "--name-only", base_str]
            else:
                cmd = ["git", "diff", "--name-only"]
        out = _run_git(cmd, p)
        return [l.strip() for l in out.splitlines() if l.strip()]
    except Exception:
        return []


def churn(path: Path | str = ".", n: int = 50) -> str:
    """Raw numstat churn: `git log --numstat --pretty=format: -n` output.

    Returns "" on error. Also exported as string for brief compatibility.
    """
    try:
        p = _resolve_path(path)
        try:
            n = int(n)
        except Exception:
            n = 50
        if n <= 0:
            n = 50
        cmd = ["git", "log", "--numstat", "--pretty=format:", f"-{n}"]
        return _run_git(cmd, p)
    except Exception:
        return ""


def git_blame(path: Path | str, file: Path | str) -> str:
    """Return `git blame <file>` output (cwd=path). Handles absolute file -> relative.

    Returns "" on error.
    """
    try:
        p = _resolve_path(path)
        # resolve file to string relative to p if possible
        f_path = Path(file)
        try:
            # If file is absolute and inside p, make relative
            if f_path.is_absolute():
                try:
                    f_rel = f_path.relative_to(p)
                    f_str = f_rel.as_posix()
                except ValueError:
                    f_str = str(f_path)
            else:
                # if file contains repo path? try to make relative
                # Check if file exists relative to p
                cand = p / f_path
                if cand.exists():
                    f_str = f_path.as_posix()
                else:
                    # file may be "a.py" without path, keep as is
                    f_str = str(f_path)
        except Exception:
            f_str = str(file)
        cmd = ["git", "blame", f_str]
        out = _run_git(cmd, p)
        if out:
            return out
        # fallback: try with original string
        if f_str != str(file):
            return _run_git(["git", "blame", str(file)], p)
        return ""
    except Exception:
        return ""


# --- hot / churn parsed ---

def git_hot(path: Path | str = ".", n: int = 50, limit: int = 10) -> list[dict]:
    """Parse churn and return ranked hot files.

    Returns list of dicts: {file, commits, added, deleted, churn} sorted by churn desc.
    """
    try:
        raw = churn(path, n=n)
        if not raw or not raw.strip():
            return []
        try:
            n = int(n)
        except Exception:
            n = 50
        try:
            limit = int(limit)
        except Exception:
            limit = 10
        if limit <= 0:
            limit = 10
        counts: dict[str, dict] = {}
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            add_s, del_s, fname = parts
            try:
                added = int(add_s) if add_s != "-" else 0
                deleted = int(del_s) if del_s != "-" else 0
            except Exception:
                continue
            fname = fname.strip()
            if not fname:
                continue
            if fname not in counts:
                counts[fname] = {"file": fname, "commits": 0, "added": 0, "deleted": 0, "churn": 0}
            counts[fname]["commits"] += 1
            counts[fname]["added"] += added
            counts[fname]["deleted"] += deleted
            counts[fname]["churn"] += added + deleted
        ranked = sorted(counts.values(), key=lambda x: x["churn"], reverse=True)
        return ranked[:limit]
    except Exception:
        return []


# Aliases for compatibility
hot_files = git_hot
get_hot = git_hot
get_churn = churn

def git_since(path: Path | str = ".", days: int = 7, n: int = 50) -> str:
    """Convenience: log since N days ago."""
    try:
        return git_log(path, n=n, since=f"{int(days)} days ago")
    except Exception:
        return ""

# for CLI wiring convenience: expose same names expected by plan snippet
# plan snippet used `churn(path, n=20)` returning raw, and `git_log`, `git_diff`, `git_blame`.
# Keep those exact names.

__all__ = ["git_log", "git_diff", "churn", "git_blame", "git_hot", "hot_files", "git_since"]
