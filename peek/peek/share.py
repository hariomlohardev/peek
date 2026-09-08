"""share — upload the HTML report to gist.github.com (issue #31).

Uses only stdlib (urllib) so `--share` works on a base install.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

GISTS_URL = "https://api.github.com/gists"


class ShareError(Exception):
    """Raised when a share upload cannot be completed."""


def _token(explicit: str | None = None) -> str:
    tok = explicit or os.environ.get("GITHUB_TOKEN")
    if not tok:
        raise ShareError(
            "Missing GITHUB_TOKEN — export GITHUB_TOKEN=<token> "
            "(needs the `gist` scope) and retry `peek --share`."
        )
    return tok


def upload_gist(
    html: str,
    filename: str = "peek-report.html",
    description: str = "peek codebase report",
    token: str | None = None,
) -> str:
    """Upload *html* as a secret gist; return the gist URL."""
    tok = _token(token)
    payload = {
        "description": description,
        "public": False,
        "files": {filename: {"content": html}},
    }
    req = urllib.request.Request(
        GISTS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {tok}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "peek-code",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        raise ShareError(
            f"gist upload failed: HTTP {e.code} — check GITHUB_TOKEN scope (`gist`)."
        ) from e
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        raise ShareError(f"gist upload failed: network error ({e}).") from e
    url = body.get("html_url") if isinstance(body, dict) else None
    if not url:
        raise ShareError("gist upload failed: unexpected API response (no html_url).")
    return url
