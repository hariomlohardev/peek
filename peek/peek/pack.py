"""Pack — smart LLM context pack.

Builds a concatenated prompt from ranked files, within token budget.
Used by `peek --pack` and `peek --pack --ask "query"`.

MVP: top N ranked files, token estimate len//4, header per file, query filter.
Falls back to scan files if no analyzer ranked.
"""

from __future__ import annotations

from pathlib import Path


def estimate_tokens(text: str) -> int:
    """Rough token estimate: 1 token ≈ 4 chars (tiktoken heuristic)."""
    return max(1, len(text) // 4)


def build_pack(
    scan_result,
    analyzer_result,
    query: str | None = None,
    token_budget: int = 8000,
    max_files: int = 12,
) -> tuple[str, list[Path], int]:
    """Build pack string.

    Returns (packed_text, included_paths, estimated_tokens).
    Never raises — returns empty on error.
    """
    try:
        # Choose file order: ranked if available else largest by LOC
        if analyzer_result and getattr(analyzer_result, "ranked", None):
            candidates = [r.path for r in analyzer_result.ranked]
            # Map path -> rel for header
            rel_map = {r.path: r.rel for r in analyzer_result.ranked}
        else:
            # fallback: scan files sorted by LOC desc
            cands = sorted(scan_result.files, key=lambda f: f.loc, reverse=True)
            candidates = [f.path for f in cands]
            rel_map = {f.path: f.rel for f in scan_result.files}

        # Filter by query if provided
        if query:
            q = query.lower()
            filtered: list[Path] = []
            for p in candidates:
                rel = rel_map.get(p, p.name)
                # rel may be Path or str
                rel_str = rel.as_posix() if isinstance(rel, Path) else str(rel)
                if q in rel_str.lower():
                    filtered.append(p)
                    continue
                # Check file content (first 200KB)
                try:
                    # quick read, handle BOM
                    try:
                        text = p.read_text(encoding="utf-8-sig", errors="ignore")
                    except Exception:
                        text = p.read_text(encoding="utf-8", errors="ignore")
                    if q in text.lower():
                        filtered.append(p)
                except Exception:
                    continue
            # If query filtered to empty, keep empty (caller will show message)
            # But if query was filename, we already filtered; if content, we have
            candidates = filtered
            if not candidates:
                return "", [], 0

        # Trim to max_files
        candidates = candidates[:max_files]

        packed_parts: list[str] = []
        included: list[Path] = []
        total_tokens = 0
        header_overhead = 0

        for p in candidates:
            try:
                # Skip binary / huge
                if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".bin"):
                    continue
                if p.stat().st_size > 500_000:
                    continue
                try:
                    text = p.read_text(encoding="utf-8-sig", errors="ignore")
                except Exception:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                if not text.strip():
                    continue
                # Header
                try:
                    rel = p.relative_to(scan_result.root).as_posix()
                except ValueError:
                    try:
                        rel = rel_map.get(p, p.name)
                        rel = rel.as_posix() if isinstance(rel, Path) else str(rel)
                    except Exception:
                        rel = p.name
                header = f"\n{'='*60}\nFILE: {rel}\n{'='*60}\n"
                chunk = header + text.strip() + "\n"
                tokens = estimate_tokens(chunk)
                if total_tokens + tokens > token_budget:
                    # Try to include truncated version if at least 1 file already included?
                    # For MVP, stop
                    break
                packed_parts.append(chunk)
                included.append(p)
                total_tokens += tokens
            except Exception:
                continue

        # Add manifest header
        manifest = f"# peek pack — {len(included)} files • ~{total_tokens} tokens • query={query or 'none'} • root={scan_result.root}\n"
        if query:
            manifest += f"# filtered by: {query!r}\n"
        manifest += "# tip: pipe to clipboard `peek --pack | clip` or `pbcopy`\n\n"
        full = manifest + "".join(packed_parts)
        # Recalculate tokens for full
        total_tokens = estimate_tokens(full)
        return full, included, total_tokens
    except Exception:
        return "", [], 0
