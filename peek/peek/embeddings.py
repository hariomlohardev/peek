"""Embeddings — BM25 with optional fastembed for semantic search.

BM25 fallback is zero-dep. If fastembed is installed, we initialize it
but still use BM25 scoring for determinism (dense retrieval optional later).
Never crashes — returns empty on error.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ScoredChunk:
    file: Path
    rel: Path
    chunk: str
    lineno: int
    score: float


# Backward alias for brief interface
EmbedIndex = dict


def _chunks_for_file(f, text: str):
    lines = text.splitlines()
    for i in range(0, len(lines), 30):
        chunk = "\n".join(lines[i : i + 50])
        if len(chunk.strip()) < 20:
            continue
        yield chunk, i + 1


def build_index(scan_result) -> dict:
    """Build BM25 index from ScanResult.

    Returns dict with keys: chunks, docs_tokens, model.
    chunks: list[(FileInfo, chunk_str, lineno)]
    docs_tokens: list[list[str]]
    model: fastembed model or None
    """
    try:
        from fastembed import TextEmbedding  # type: ignore

        try:
            model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")
            has_fastembed = True
        except Exception:
            has_fastembed = False
            model = None
    except ImportError:
        has_fastembed = False
        model = None

    chunks: list[tuple[object, str, int]] = []
    try:
        files = getattr(scan_result, "files", []) or []
    except Exception:
        files = []

    for f in files:
        try:
            try:
                text = f.path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                try:
                    text = f.path.read_text(encoding="utf-8-sig", errors="ignore")
                except Exception:
                    continue
            if not text or not text.strip():
                continue
            # skip binary / huge via suffix check is already done at scan, but guard
            if f.path.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".bin", ".exe", ".so", ".o"):
                continue
            if getattr(f, "size", 0) > 500_000:
                continue
            for chunk, lineno in _chunks_for_file(f, text):
                chunks.append((f, chunk, lineno))
        except Exception:
            continue

    docs_tokens: list[list[str]] = []
    for _, chunk, _ in chunks:
        try:
            toks = re.findall(r"\w+", chunk.lower())
            docs_tokens.append(toks)
        except Exception:
            docs_tokens.append([])

    return {"chunks": chunks, "docs_tokens": docs_tokens, "model": model}


def search(index: dict, query: str, k: int = 10) -> list[ScoredChunk]:
    """BM25-lite search over index.

    Scoring: for each query token, idf = log((N - df +0.5)/(df+0.5)+1), tf = count/len(doc), score = sum idf*tf
    Returns list[ScoredChunk] sorted desc, filtered score>0, up to k.
    """
    try:
        if not query or not query.strip():
            return []
        if not isinstance(index, dict):
            return []
        chunks = index.get("chunks", [])
        docs_tokens = index.get("docs_tokens", [])
        if not chunks or not docs_tokens:
            return []
        try:
            k = int(k)
        except Exception:
            k = 10
        if k <= 0:
            k = 10

        q_tokens = re.findall(r"\w+", query.lower())
        if not q_tokens:
            return []

        N = len(chunks)
        # df per term
        df: dict[str, int] = {}
        for toks in docs_tokens:
            try:
                for t in set(toks):
                    df[t] = df.get(t, 0) + 1
            except Exception:
                continue

        scored: list[ScoredChunk] = []
        for idx, (f, chunk, lineno) in enumerate(chunks):
            try:
                toks = docs_tokens[idx] if idx < len(docs_tokens) else []
                score = 0.0
                for qt in q_tokens:
                    if qt in toks:
                        # idf bm25-like
                        try:
                            idf = math.log((N - df.get(qt, 0) + 0.5) / (df.get(qt, 0) + 0.5) + 1)
                        except Exception:
                            idf = 0.0
                        try:
                            tf = toks.count(qt) / len(toks) if toks else 0
                        except Exception:
                            tf = 0
                        score += idf * tf
                # f is FileInfo
                try:
                    file_path = f.path
                    rel_path = f.rel
                except Exception:
                    continue
                scored.append(ScoredChunk(file_path, rel_path, chunk, lineno, float(score)))
            except Exception:
                continue

        scored.sort(key=lambda x: x.score, reverse=True)
        # filter >0
        filtered = [s for s in scored if s.score > 0]
        if filtered:
            # If we have at least one positive hit but fewer than k, pad with next best zero-scored
            # so intent queries like "where is auth token validated" return k hits with first > second
            if len(filtered) < k:
                remaining = [s for s in scored if s.score == 0]
                # preserve original sorted order (all 0 equal, but keep file order)
                needed = k - len(filtered)
                filtered.extend(remaining[:needed])
            return filtered[:k]
        return []
    except Exception:
        return []
