"""Find — keyword search over codebase.

Used by `peek find <query> [PATH]` and `peek --find <query>`.

Ranks by analyzer score + keyword match strength.
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
        q = query.lower().strip()
        # Map path -> analyzer score
        score_map: dict[Path, float] = {}
        if analyzer_result and getattr(analyzer_result, "ranked", None):
            for r in analyzer_result.ranked:
                score_map[r.path] = r.score
        # Also map for quick rel
        rel_map: dict[Path, Path] = {f.path: f.rel for f in scan_result.files}

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

            total = filename_score + content_score + base_score
            if total <= 0:
                continue
            # Only include if at least filename or content matched
            if filename_score == 0 and content_score == 0:
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
