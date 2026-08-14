"""Pack — smart LLM context pack.

Builds a concatenated prompt from ranked files, within token budget.
Used by `peek --pack` and `peek --pack --ask "query"`.

v2: token-smart, format md/xml/txt, include/exclude globs, budget.
v3: semantic ranking via BM25 when query contains spaces or index available.

MVP: top N ranked files, token estimate len//4, header per file, query filter.
Falls back to scan files if no analyzer ranked.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path


def estimate_tokens(text: str) -> int:
    """Rough token estimate: 1 token ≈ 4 chars (tiktoken heuristic)."""
    return max(1, len(text) // 4)


def _glob_match(rel_posix: str, pattern: str) -> bool:
    """Match glob pattern against rel posix.

    Supports fnmatch on full path, basename fallback for '*.py' to match subdirs,
    and pathlib Path.match for ** patterns.
    """
    if not pattern:
        return False
    # direct fnmatch on full posix
    try:
        if fnmatch.fnmatch(rel_posix, pattern):
            return True
    except Exception:
        pass
    # basename fallback — so "*.py" matches "sub/a.py"
    try:
        if fnmatch.fnmatch(Path(rel_posix).name, pattern):
            return True
    except Exception:
        pass
    # pathlib match handles ** and other glob features
    try:
        if Path(rel_posix).match(pattern):
            return True
    except Exception:
        pass
    return False


def build_pack(
    scan_result,
    analyzer_result,
    query: str | None = None,
    budget: int = 8000,
    format: str = "md",
    include: str | None = None,
    exclude: str | None = None,
    token_budget: int | None = None,
    max_files: int = 12,
) -> tuple[str, list[Path], int]:
    """Build pack string.

    Args:
        scan_result: ScanResult from peek.scanner
        analyzer_result: AnalyzerResult from peek.analyzer (may be None)
        query: optional keyword filter
        budget: token budget (alias token_budget for backwards compat)
        format: "md" | "xml" | "txt"
        include: glob to include (e.g. "*.py" or "src/**/*.py")
        exclude: glob to exclude
        token_budget: backwards compat alias for budget
        max_files: hard cap on files

    Returns (packed_text, included_paths, estimated_tokens).
    Never raises — returns empty on error.
    """
    try:
        # Normalize budget alias
        if token_budget is not None:
            try:
                budget = int(token_budget)
            except Exception:
                budget = 8000
        try:
            budget = int(budget)
        except Exception:
            budget = 8000
        if budget <= 0:
            budget = 8000

        # Normalize format
        if format not in ("md", "xml", "txt"):
            format = "md"
        # Normalize max_files
        try:
            max_files = int(max_files)
        except Exception:
            max_files = 12
        if max_files <= 0:
            max_files = 12

        # Filter FileInfos by include/exclude for fallback path
        # Keep original scan files for language lookup
        try:
            all_files = list(scan_result.files) if scan_result and getattr(scan_result, "files", None) is not None else []
        except Exception:
            all_files = []

        filtered_infos = all_files
        if include:
            filtered_infos = [f for f in filtered_infos if _glob_match(f.rel.as_posix(), include)]
        if exclude:
            filtered_infos = [f for f in filtered_infos if not _glob_match(f.rel.as_posix(), exclude)]

        # Build lookup for language and rel fallback
        info_by_path: dict[Path, object] = {}
        info_by_resolved: dict[Path, object] = {}
        for fi in all_files:
            try:
                info_by_path[fi.path] = fi
                info_by_resolved[fi.path.resolve()] = fi
            except Exception:
                try:
                    info_by_path[fi.path] = fi
                except Exception:
                    pass

        # Choose file order: ranked if available else largest by LOC (filtered)
        if analyzer_result and getattr(analyzer_result, "ranked", None):
            candidates = [r.path for r in analyzer_result.ranked]
            rel_map = {r.path: r.rel for r in analyzer_result.ranked}
            # Filter ranked candidates by include/exclude (using rel)
            if include or exclude:
                filtered_candidates: list[Path] = []
                for p in candidates:
                    rel = rel_map.get(p, p.name)
                    rel_str = rel.as_posix() if isinstance(rel, Path) else str(rel)
                    if include and not _glob_match(rel_str, include):
                        continue
                    if exclude and _glob_match(rel_str, exclude):
                        continue
                    filtered_candidates.append(p)
                candidates = filtered_candidates
        else:
            # fallback: scan files sorted by LOC desc (already filtered)
            cands = sorted(filtered_infos, key=lambda f: getattr(f, "loc", 0), reverse=True)
            candidates = [f.path for f in cands]
            rel_map = {f.path: f.rel for f in filtered_infos}
            # Also need rel_map for candidates that may not be in filtered_infos? Already.

        # Filter by query if provided
        if query:
            # Try semantic search first (BM25) when index available
            semantic_done = False
            try:
                from peek.embeddings import build_index, search

                idx = build_index(scan_result)
                hits = search(idx, query, k=max_files * 4 if max_files else 20)
                if hits:
                    # Map file -> best semantic score (dedup chunks)
                    file_to_score: dict[Path, float] = {}
                    for h in hits:
                        try:
                            # Respect include/exclude already applied to candidates via rel_map
                            # Only consider files that are in candidates set (filtered)
                            if h.file not in set(candidates):
                                # Also check resolved equality
                                # hits may have resolved paths, candidates may be unresolved — normalize
                                found = False
                                for c in candidates:
                                    try:
                                        if c.resolve() == h.file.resolve():
                                            # use candidate path as key
                                            if c not in file_to_score or h.score > file_to_score[c]:
                                                file_to_score[c] = h.score
                                            found = True
                                            break
                                    except Exception:
                                        continue
                                if not found:
                                    continue
                            else:
                                if h.file not in file_to_score or h.score > file_to_score[h.file]:
                                    file_to_score[h.file] = h.score
                        except Exception:
                            continue
                    # Boost filename matches (so auth.py ranks for "auth" even if content lacks token)
                    try:
                        q_tokens = re.findall(r"\w+", query.lower())
                        for p in list(candidates):
                            rel = rel_map.get(p, p.name)
                            rel_str = rel.as_posix() if isinstance(rel, Path) else str(rel)
                            rel_low = rel_str.lower()
                            fname_bonus = 0.0
                            for tok in q_tokens:
                                if tok in rel_low:
                                    fname_bonus += 5.0
                            if fname_bonus > 0:
                                file_to_score[p] = file_to_score.get(p, 0.0) + fname_bonus
                    except Exception:
                        pass
                    if file_to_score:
                        # Rank candidates by semantic + filename score desc
                        ranked = sorted(candidates, key=lambda p: file_to_score.get(p, -1), reverse=True)
                        # Keep only those with score >0
                        filtered_sem = [p for p in ranked if file_to_score.get(p, 0) > 0]
                        if filtered_sem:
                            candidates = filtered_sem
                            semantic_done = True
                        else:
                            # semantic produced no positive after boost -> fallback
                            semantic_done = False
                    else:
                        semantic_done = False
                else:
                    semantic_done = False
            except Exception:
                semantic_done = False

            if not semantic_done:
                q = query.lower()
                filtered: list[Path] = []
                for p in candidates:
                    rel = rel_map.get(p, p.name)
                    rel_str = rel.as_posix() if isinstance(rel, Path) else str(rel)
                    if q in rel_str.lower():
                        filtered.append(p)
                        continue
                    # Check file content (first 500KB already guarded)
                    try:
                        try:
                            text = p.read_text(encoding="utf-8-sig", errors="ignore")
                        except Exception:
                            text = p.read_text(encoding="utf-8", errors="ignore")
                        if q in text.lower():
                            filtered.append(p)
                    except Exception:
                        continue
                candidates = filtered
                if not candidates:
                    return "", [], 0

        # Trim to max_files
        candidates = candidates[:max_files]

        packed_parts: list[str] = []
        included: list[Path] = []
        total_tokens = 0

        for p in candidates:
            try:
                # Skip binary / huge
                if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".bin"):
                    continue
                try:
                    if p.stat().st_size > 500_000:
                        continue
                except Exception:
                    pass
                try:
                    text = p.read_text(encoding="utf-8-sig", errors="ignore")
                except Exception:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                if not text.strip():
                    continue
                # Resolve rel string
                try:
                    rel = p.relative_to(scan_result.root).as_posix()
                except ValueError:
                    try:
                        rel_obj = rel_map.get(p, p.name)
                        rel = rel_obj.as_posix() if isinstance(rel_obj, Path) else str(rel_obj)
                    except Exception:
                        rel = p.name
                except Exception:
                    rel = p.name

                # language for md fence
                lang = "text"
                try:
                    # try resolved lookup
                    fi = info_by_resolved.get(p.resolve())
                    if fi is None:
                        fi = info_by_path.get(p)
                    if fi is not None and hasattr(fi, "language"):
                        lang = getattr(fi, "language", "text") or "text"
                        # Normalize python -> python, etc.
                        if lang == "other":
                            # infer from suffix
                            ext = p.suffix.lower()
                            if ext == ".py":
                                lang = "python"
                            elif ext in (".js", ".jsx"):
                                lang = "javascript"
                            elif ext in (".ts", ".tsx"):
                                lang = "typescript"
                    else:
                        # infer
                        ext = p.suffix.lower()
                        if ext == ".py":
                            lang = "python"
                        elif ext == ".md":
                            lang = "markdown"
                except Exception:
                    lang = "text"

                # Format chunk per format
                if format == "xml":
                    # Use CDATA, ensure not breaking on ]]>
                    safe = text.strip().replace("]]>", "]]&gt;")
                    chunk = f'<file path="{rel}">\n<![CDATA[\n{safe}\n]]>\n</file>'
                elif format == "txt":
                    chunk = f'# {rel}\n{text.strip()}'
                else:  # md
                    # Include FILE: marker for backwards compat with old tests that check "FILE:"
                    # Also keep markdown fence for new behavior
                    chunk = f'## {rel}\nFILE: {rel}\n```{lang}\n{text.strip()}\n```'

                tokens = estimate_tokens(chunk)
                if total_tokens + tokens > budget:
                    break
                packed_parts.append(chunk)
                included.append(p)
                total_tokens += tokens
            except Exception:
                continue

        if not included:
            # If no files included due to filters/budget, return empty if query was set? But for no query, empty is also empty
            # Return empty correctly
            if not packed_parts:
                return "", [], 0

        # Join parts per format
        if format == "xml":
            body = "\n".join(packed_parts)
            # XML manifest as comment
            manifest = f"<!-- peek pack — {len(included)} files • ~{total_tokens} tokens • query={query or 'none'} • root={scan_result.root} • format={format} -->\n"
            full = manifest + body + "\n"
        elif format == "txt":
            body = "\n\n".join(packed_parts)
            manifest = f"# peek pack — {len(included)} files • ~{total_tokens} tokens • query={query or 'none'} • root={scan_result.root} • format={format}\n# tip: pipe to clipboard `peek --pack | clip` or `pbcopy`\n\n"
            full = manifest + body + "\n"
        else:  # md
            body = "\n\n".join(packed_parts)
            manifest = f"# peek pack — {len(included)} files • ~{total_tokens} tokens • query={query or 'none'} • root={scan_result.root} • format={format}\n"
            if query:
                manifest += f"# filtered by: {query!r}\n"
            if include:
                manifest += f"# include: {include!r}\n"
            if exclude:
                manifest += f"# exclude: {exclude!r}\n"
            manifest += "# tip: pipe to clipboard `peek --pack | clip` or `pbcopy`\n\n"
            full = manifest + body + "\n"

        # Recalculate tokens for full
        total_tokens = estimate_tokens(full)
        return full, included, total_tokens
    except Exception:
        return "", [], 0
