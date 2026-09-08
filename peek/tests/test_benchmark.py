"""Issue #104 — 10k-file monorepo ceiling (skipped by default: slow).

Run explicitly:  PEEK_BENCH=1 pytest peek/tests/test_benchmark.py -v -s
"""

import os
import time

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("PEEK_BENCH") != "1",
    reason="slow benchmark — set PEEK_BENCH=1 to run",
)


def _make_monorepo(root, n=10_000):
    for i in range(n):
        mod = root / f"pkg{i // 100}" / f"mod{i}.py"
        mod.parent.mkdir(parents=True, exist_ok=True)
        # small hub/spoke shape so PageRank has something to chew on
        dep = f"import mod{i - 1}\n" if i % 100 else ""
        mod.write_text(f"{dep}x_{i} = {i}\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\nname = 'big'\n", encoding="utf-8")
    (root / "README.md").write_text("# big\n", encoding="utf-8")


def test_scan_10k_monorepo(tmp_path):
    from peek.scanner import scan

    _make_monorepo(tmp_path)
    t0 = time.perf_counter()
    sr = scan(tmp_path, max_files=20_000)
    scan_s = time.perf_counter() - t0
    print(f"\nscan 10k files: {scan_s:.2f}s")
    assert sr.total_files >= 10_000  # 10k .py + pyproject.toml + README.md
    assert not sr.stats["truncated"]


def test_analyze_10k_monorepo(tmp_path):
    from peek.analyzer import analyze
    from peek.scanner import scan

    _make_monorepo(tmp_path)
    sr = scan(tmp_path, max_files=20_000)
    t0 = time.perf_counter()
    ar = analyze(sr)
    analyze_s = time.perf_counter() - t0
    print(f"\nanalyze 10k files: {analyze_s:.2f}s ({len(ar.graph)} nodes)")
    assert len(ar.ranked) > 0


def test_default_cap_truncates_10k(tmp_path):
    from peek.scanner import scan

    _make_monorepo(tmp_path)
    sr = scan(tmp_path)  # default max_files=2000
    assert sr.stats["truncated"]
    assert sr.total_files == 2000
