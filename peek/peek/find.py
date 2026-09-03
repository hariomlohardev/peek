"""Find — keyword search + semantic BM25 over codebase.

Used by `peek find <query> [PATH]` and `peek --find <query>`.

Ranks by analyzer score + keyword match strength.
If query contains spaces (intent), tries semantic BM25 via peek.embeddings.

Never crashes.
"""

from __future__ import annotations

from pathlib import Path


def find_matches(
    query: str,
    scan_result,
    analyzer_result,
    limit: int = 20,
) -> list[dict]:
    """Search for query in filenames and file contents.

    Returns list of dicts: {path, rel, score, reason, preview_lines}
    Sorted by combined score desc. Never raises.
    """
    try:
        if not query or not query.strip():
            return []
        # Semantic path: if query is multi-word (intent), try embeddings.search
        if " " in query.strip():
            try:
                from peek.embeddings import build_index, search

                idx = build_index(scan_result)
                hits = search(idx, query, k=limit)
                # Filter to positive semantic hits only (search may pad zeros for test_bm25_fallback)
                hits = [h for h in hits if getattr(h, "score", 0) > 0]
                if hits:
                    # Map analyzer scores for tie-break / reason
                    score_map: dict[Path, float] = {}
                    if analyzer_result and getattr(analyzer_result, "ranked", None):
                        for r in analyzer_result.ranked:
                            score_map[r.path] = r.score
                    # Map rel and loc for completeness
                    loc_map: dict[Path, int] = {}
                    if scan_result and getattr(scan_result, "files", None):
                        for f in scan_result.files:
                            try:
                                loc_map[f.path] = f.loc
                            except Exception:
                                pass
                    out: list[dict] = []
                    for h in hits:
                        # Build preview from chunk (first 3 lines)
                        preview: list[str] = []
                        try:
                            lines = h.chunk.splitlines()
                            for li, line in enumerate(lines[:3], start=h.lineno):
                                snippet = line.strip()[:120]
                                if len(line.strip()) > 120:
                                    snippet += "…"
                                if snippet:
                                    preview.append(f"{li:>4}: {snippet}")
                        except Exception:
                            preview = []
                        # Combine semantic score with analyzer base (weighted)
                        base = score_map.get(h.file, 0.0) * 0.1
                        total = float(h.score) * 10.0 + base
                        reason = "semantic"
                        if h.file in score_map:
                            reason += f" • ranked {score_map[h.file]:.1f}"
                        out.append(
                            {
                                "path": h.file,
                                "rel": h.rel,
                                "score": round(float(total), 2),
                                "reason": reason,
                                "preview": preview,
                                "loc": loc_map.get(h.file, 0),
                                "analyzer_score": round(float(score_map.get(h.file, 0.0)), 2),
                            }
                        )
                    # Deduplicate by path (keep highest scored chunk per file)
                    dedup: dict[Path, dict] = {}
                    for m in out:
                        p = m["path"]
                        if p not in dedup or m["score"] > dedup[p]["score"]:
                            dedup[p] = m
                    deduped = list(dedup.values())
                    deduped.sort(key=lambda x: (x["score"], x["analyzer_score"]), reverse=True)
                    if deduped:
                        return deduped[:limit]
                # if no hits, fall through to keyword
            except Exception:
                pass
        q = query.lower().strip()
        # Map path -> analyzer score
        score_map: dict[Path, float] = {}
        if analyzer_result and getattr(analyzer_result, "ranked", None):
            for r in analyzer_result.ranked:
                score_map[r.path] = r.score
        # Also map for quick rel
        rel_map: dict[Path, Path] = {f.path: f.rel for f in scan_result.files}

        # Where the query is *declared*, not merely mentioned.
        #
        # Content scoring counts occurrences, so a file that names something eight
        # times in comments outranked the one file that defines it -- which is the
        # opposite of what someone typing a symbol name wants. A declaration is a
        # different kind of hit, so it scores separately rather than as more content.
        symbol_hits: dict[Path, tuple[str, str, int]] = {}
        try:
            from peek.symbols import index_symbols

            for sym in index_symbols(scan_result):
                if sym.name.lower() != q:
                    continue
                # First declaration per file wins: a name is usually defined once,
                # and where it is not, the earliest is the one to jump to.
                if sym.file not in symbol_hits:
                    symbol_hits[sym.file] = (sym.kind, sym.name, sym.lineno)
        except Exception:
            # Symbol indexing is an enhancement to ranking, never a reason to fail
            # a search -- `find_matches` never raises.
            symbol_hits = {}

        results: list[dict] = []
        for f in scan_result.files:
            # Skip binary / huge / no loc
            if f.path.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".bin", ".exe", ".so", ".o"):
                continue
            if f.size > 500_000:
                continue
            rel_str = f.rel.as_posix().lower()
            filename_score = 0
            reason_parts: list[str] = []
            # Filename match — strongest
            if q in rel_str:
                filename_score = 10.0
                reason_parts.append("filename")
                # Bonus if exact filename
                if f.rel.name.lower() == q or f.rel.stem.lower() == q:
                    filename_score += 5.0
                    reason_parts.append("exact")
            # Analyzer score base
            base_score = score_map.get(f.path, 0.0) * 0.3  # weight down

            # Content match — need to read
            content_score = 0.0
            preview: list[str] = []
            try:
                # Only read if filename didn't already strongly match, or still need preview
                try:
                    text = f.path.read_text(encoding="utf-8-sig", errors="ignore")
                except Exception:
                    text = f.path.read_text(encoding="utf-8", errors="ignore")
                if text.startswith("﻿"):
                    text = text.lstrip("﻿")
                lower_text = text.lower()
                if q in lower_text:
                    # Count occurrences (capped)
                    occ = lower_text.count(q)
                    content_score = min(5.0 + occ * 0.5, 8.0)
                    reason_parts.append(f"content ×{occ}")
                    # Extract preview lines (up to 3)
                    lines = text.splitlines()
                    for idx, line in enumerate(lines, 1):
                        if q in line.lower():
                            # Trim long lines
                            snippet = line.strip()[:120]
                            if len(line.strip()) > 120:
                                snippet += "…"
                            preview.append(f"{idx:>4}: {snippet}")
                            if len(preview) >= 3:
                                break
                else:
                    # No match at all
                    if filename_score == 0:
                        continue
            except Exception:
                # If read fails but filename matched, keep it
                if filename_score == 0:
                    continue
                preview = []

            # A declaration outweighs a filename match, which already outweighs
            # content: `peek find Bar` should land on `class Bar` before it lands
            # on a file merely called bar.py.
            symbol_score = 0.0
            declared = symbol_hits.get(f.path)
            if declared is not None:
                kind, name, lineno = declared
                symbol_score = 12.0
                reason_parts.insert(0, f"{'class' if kind == 'class' else 'def'} {name}")
                # The declaration line leads the preview: it is what the reader
                # asked for, and burying it under three comment lines is the same
                # failure as ranking the file below them.
                preview = [line for line in preview if not line.startswith(f"{lineno:>4}:")]
                try:
                    source = f.path.read_text(encoding="utf-8", errors="ignore").splitlines()
                    preview.insert(0, f"{lineno:>4}: {source[lineno - 1].strip()[:120]}")
                except Exception:
                    pass
                preview = preview[:3]

            total = filename_score + content_score + base_score + symbol_score
            if total <= 0:
                continue
            # Only include if at least filename, content or a declaration matched
            if filename_score == 0 and content_score == 0 and symbol_score == 0:
                continue

            # Use analyzer reason for tie-break? Keep original why
            reason = ", ".join(reason_parts) if reason_parts else "match"
            # Boost if analyzer already marked as hub/entry and content matched
            if content_score > 0 and f.path in score_map:
                reason += f" • ranked {score_map[f.path]:.1f}"

            results.append(
                {
                    "path": f.path,
                    "rel": f.rel,
                    "score": round(float(total), 2),
                    "reason": reason,
                    "preview": preview,
                    "loc": f.loc,
                    "analyzer_score": round(float(score_map.get(f.path, 0.0)), 2),
                }
            )
        # Sort by total score desc, then analyzer score
        results.sort(key=lambda x: (x["score"], x["analyzer_score"]), reverse=True)
        return results[:limit]
    except Exception:
        return []
