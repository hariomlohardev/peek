#!/usr/bin/env python3
"""
Create a GitHub issue with dedupe check — search open issues for normalized title match before creating.

Usage:
  python scripts/create_issue.py --title "Good First Issue: Add Go..." --body "..." --labels "good first issue,enhancement"

This prevents the duplicate backlog that happened in Aug 2025 when 20 issues were re-created as 63.
"""

import argparse, os, re, sys, requests

def normalize_title(t: str) -> str:
    # Lowercase, strip "Good First Issue:" prefix, collapse whitespace, remove punctuation
    t = t.lower()
    t = re.sub(r"^good first issue:\s*", "", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(t.split()).strip()

def main():
    ap = argparse.ArgumentParser(description="Create issue with dedupe")
    ap.add_argument("--title", required=True)
    ap.add_argument("--body", required=True)
    ap.add_argument("--labels", default="good first issue")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Missing GITHUB_PERSONAL_ACCESS_TOKEN or GITHUB_TOKEN", file=sys.stderr)
        sys.exit(1)

    owner, repo = "hariomlohardev", "peek"
    base = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

    # Fetch open issues (first 100) and check for normalized title match
    r = requests.get(f"{base}/issues?state=open&per_page=100", headers=headers)
    r.raise_for_status()
    open_issues = r.json()
    norm_new = normalize_title(args.title)
    for iss in open_issues:
        norm_existing = normalize_title(iss["title"])
        if norm_new == norm_existing:
            print(f"Duplicate found: #{iss['number']} has same normalized title '{norm_existing}' — not creating new issue.")
            print(f"Existing: {iss['html_url']}")
            sys.exit(0)
        # Also check if new title is substring of existing or vice versa (for polyglot splits)
        # e.g., "Add Go language detection" vs "Add Go language detection + symbol regex" — treat as not duplicate, allow

    # No duplicate — create
    labels = [l.strip() for l in args.labels.split(",") if l.strip()]
    data = {"title": args.title, "body": args.body, "labels": labels}
    r2 = requests.post(f"{base}/issues", headers=headers, json=data)
    if r2.status_code == 201:
        j = r2.json()
        print(f"Created #{j['number']}: {j['html_url']}")
    else:
        print(f"Failed {r2.status_code}: {r2.text[:500]}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
