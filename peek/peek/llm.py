"""LLM — optional AI summary.

If OPENAI_API_KEY or ANTHROPIC_API_KEY is set, tries to call a cheap model
for a better codebase summary. Falls back to heuristic otherwise.

MVP: no hard dependency on openai/anthropic — try import, else None.
`peek --llm` forces attempt; `peek` without --llm only uses LLM if env var
and package available.
"""

from __future__ import annotations

import os
from pathlib import Path


def _build_prompt(scan_result, analyzer_result) -> str:
    """Build concise prompt for LLM."""
    try:
        parts: list[str] = []
        parts.append(f"Project at {scan_result.root}")
        parts.append(f"Files: {scan_result.stats.get('total_files',0)}, LOC: {scan_result.stats.get('total_loc',0)}")
        parts.append(f"Languages: {scan_result.stats.get('by_lang',{})}")
        if scan_result.tech_stack:
            parts.append(f"Tech stack: {scan_result.tech_stack}")
        if analyzer_result:
            parts.append(f"Summary (heuristic): {analyzer_result.summary}")
            parts.append(f"Top files:")
            for r in analyzer_result.ranked[:6]:
                parts.append(f"  - {r.rel.as_posix()} (score {r.score:.1f}, {', '.join(r.reasons)})")
            if analyzer_result.graph:
                edge_str = []
                for src, deps in list(analyzer_result.graph.items())[:4]:
                    try:
                        s = src.relative_to(analyzer_result.root).as_posix()
                    except ValueError:
                        s = src.name
                    ds = []
                    for d in list(deps)[:2]:
                        try:
                            ds.append(d.relative_to(analyzer_result.root).as_posix())
                        except ValueError:
                            ds.append(d.name)
                    if ds:
                        edge_str.append(f"{s} -> {', '.join(ds)}")
                parts.append(f"Graph: {'; '.join(edge_str)}")
        parts.append("Task: Summarize this codebase in 2-3 sentences. What is it, what tech, where to start?")
        return "\n".join(parts)
    except Exception:
        return "Summarize this codebase."


def try_llm_summary(scan_result, analyzer_result, force: bool = False) -> str | None:
    """Try to get LLM summary. Returns None if not available or fails.

    Checks env vars: OPENAI_API_KEY, ANTHROPIC_API_KEY.
    If `force` is False, only tries if key is set and package importable.
    If `force` is True, tries even if key missing but will quickly fail and return None.
    """
    # Check if any key is set (or force)
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if not force and not (has_openai or has_anthropic):
        return None

    prompt = _build_prompt(scan_result, analyzer_result)

    # Try OpenAI first
    if has_openai or force:
        try:
            # Try new openai>=1.0 API
            try:
                from openai import OpenAI  # type: ignore

                client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
                # Use cheap model
                resp = client.chat.completions.create(
                    model=os.environ.get("PEEK_LLM_MODEL", "gpt-4o-mini"),
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,
                    temperature=0.2,
                )
                text = resp.choices[0].message.content
                if text and text.strip():
                    return text.strip()
            except ImportError:
                # Try old openai 0.x
                import openai  # type: ignore

                openai.api_key = os.environ.get("OPENAI_API_KEY", "")
                resp = openai.ChatCompletion.create(  # type: ignore
                    model=os.environ.get("PEEK_LLM_MODEL", "gpt-3.5-turbo"),
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,
                    temperature=0.2,
                )
                text = resp["choices"][0]["message"]["content"]
                if text and text.strip():
                    return text.strip()
            except Exception:
                # Fall through to anthropic
                pass
        except Exception:
            pass

    # Try Anthropic
    if has_anthropic or force:
        try:
            import anthropic  # type: ignore

            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
            resp = client.messages.create(
                model=os.environ.get("PEEK_LLM_MODEL", "claude-3-haiku-20240307"),
                max_tokens=300,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            )
            # resp.content is list of blocks
            if resp.content and len(resp.content) > 0:
                text = resp.content[0].text  # type: ignore
                if text and text.strip():
                    return text.strip()
        except ImportError:
            pass
        except Exception:
            pass

    return None
