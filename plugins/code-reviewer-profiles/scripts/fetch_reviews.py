#!/usr/bin/env python3
"""
Fetch GitHub code review data for a user and cache it locally.

Uses the `gh` CLI for all GitHub API interactions. Stdlib only — no pip packages needed.

Usage:
    python3 fetch_reviews.py --user=octocat --cache-dir=/tmp/reviews --limit=150
    python3 fetch_reviews.py --user=jsmith --host=github.enterprise.com --cache-dir=./cache

Features:
    - Auto-detects GitHub host from `gh auth status` if --host not provided
    - Checkpoint/resume: re-running picks up where it left off
    - Marks trivial comments (LGTM, etc.) with "trivial": true
    - Normalizes file extensions using pathlib
    - Builds index.json at the end
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Trivial-comment detection
# ---------------------------------------------------------------------------

TRIVIAL_PATTERNS = [
    re.compile(r"^LGTM!?$"),
    re.compile(r"^[Ll]ooks good!?\.?$"),
    re.compile(r"^[Aa]pproved\.?$"),
    re.compile(r"^👍$"),
    re.compile(r"^✅$"),
    re.compile(r"^[Nn]ice!?$"),
    re.compile(r"^[Ss]hip it!?$"),
    re.compile(r"^[Gg]ood call!?$"),
    re.compile(r"^[Ss]hipping!?$"),
]


def is_trivial(body: str) -> bool:
    """Return True if the comment body matches a trivial/approval pattern."""
    text = body.strip()
    return any(p.match(text) for p in TRIVIAL_PATTERNS)


# ---------------------------------------------------------------------------
# File-extension normalisation
# ---------------------------------------------------------------------------

SPECIAL_FILENAMES = {"Dockerfile", "Makefile", "Jenkinsfile", "Vagrantfile", "Rakefile"}


def get_extension(path: str) -> str:
    """Extract a normalised file extension from a path."""
    p = Path(path)
    if p.name in SPECIAL_FILENAMES:
        return p.name
    if p.name.startswith("."):
        return p.name  # .gitignore, .editorconfig, etc.
    return p.suffix.lstrip(".") if p.suffix else "no-extension"


# ---------------------------------------------------------------------------
# GitHub host detection
# ---------------------------------------------------------------------------

def detect_host() -> str:
    """Auto-detect the GitHub host from `gh auth status`."""
    result = subprocess.run(
        ["gh", "auth", "status"],
        capture_output=True, text=True,
    )
    # gh auth status prints to stderr
    output = result.stderr + result.stdout
    # Look for lines like "  github.com" or "  github.enterprise.com"
    # The format is: "  <host>\n    ..."
    for line in output.splitlines():
        stripped = line.strip()
        if stripped and "Logged in" in stripped:
            # "Logged in to github.com account ..."
            parts = stripped.split()
            for i, part in enumerate(parts):
                if part == "to" and i + 1 < len(parts):
                    candidate = parts[i + 1].rstrip(",")
                    if "." in candidate:
                        return candidate
    # Fallback: look for any hostname pattern
    for line in output.splitlines():
        stripped = line.strip()
        if re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", stripped):
            return stripped
    return "github.com"


# ---------------------------------------------------------------------------
# gh CLI helpers
# ---------------------------------------------------------------------------

def gh_env(host: str) -> dict:
    """Build environment dict, setting GH_HOST for non-github.com hosts."""
    env = os.environ.copy()
    if host != "github.com":
        env["GH_HOST"] = host
    return env


def run_gh(args: list[str], host: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a gh CLI command with the correct host environment."""
    return subprocess.run(
        ["gh"] + args,
        capture_output=True, text=True,
        env=gh_env(host),
        check=check,
    )


def parse_paginated_json(text: str) -> list:
    """Parse potentially multiple concatenated JSON arrays from `gh api --paginate`."""
    if not text.strip():
        return []
    decoder = json.JSONDecoder()
    results = []
    idx = 0
    text = text.strip()
    while idx < len(text):
        # Skip whitespace
        while idx < len(text) and text[idx] in " \t\n\r":
            idx += 1
        if idx >= len(text):
            break
        obj, end_idx = decoder.raw_decode(text, idx)
        if isinstance(obj, list):
            results.extend(obj)
        else:
            results.append(obj)
        idx = end_idx
    return results


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def load_checkpoint(cache_dir: Path) -> dict | None:
    """Load checkpoint from cache dir, or return None."""
    cp_file = cache_dir / "checkpoint.json"
    if cp_file.exists():
        try:
            with open(cp_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
    return None


def save_checkpoint(cache_dir: Path, last_index: int, pr_list: list):
    """Save checkpoint with last processed index and the full PR list."""
    cp_file = cache_dir / "checkpoint.json"
    with open(cp_file, "w") as f:
        json.dump({
            "last_index": last_index,
            "pr_list": pr_list,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }, f)


def clear_checkpoint(cache_dir: Path):
    """Remove checkpoint file after successful completion."""
    cp_file = cache_dir / "checkpoint.json"
    if cp_file.exists():
        cp_file.unlink()


# ---------------------------------------------------------------------------
# PR search
# ---------------------------------------------------------------------------

def search_prs(user: str, host: str, limit: int) -> list[dict]:
    """Search for merged PRs reviewed by the user. Handles pagination via date windowing."""
    all_prs = []
    remaining = limit
    last_date = None

    while remaining > 0:
        batch_size = min(remaining, 100)
        args = [
            "search", "prs",
            f"--reviewed-by={user}",
            "--merged",
            f"--limit={batch_size}",
            "--json", "number,title,repository,closedAt,url",
        ]
        if last_date:
            args.append(f"--merged-at=<{last_date}")

        result = run_gh(args, host, check=False)
        if result.returncode != 0:
            print(f"  Warning: PR search failed: {result.stderr.strip()}", file=sys.stderr)
            break

        batch = json.loads(result.stdout) if result.stdout.strip() else []
        if not batch:
            break

        all_prs.extend(batch)
        remaining -= len(batch)

        if len(batch) < batch_size:
            break  # No more results

        # Use oldest closedAt as the window boundary
        dates = [pr.get("closedAt", "") for pr in batch if pr.get("closedAt")]
        if dates:
            last_date = min(dates)
        else:
            break

    # Deduplicate by (repo fullName, number)
    seen = set()
    unique = []
    for pr in all_prs:
        repo = pr["repository"]["nameWithOwner"]
        key = (repo, pr["number"])
        if key not in seen:
            seen.add(key)
            unique.append(pr)
    return unique[:limit]


# ---------------------------------------------------------------------------
# Fetch comments for a single PR
# ---------------------------------------------------------------------------

def fetch_pr_data(pr: dict, user: str, host: str) -> dict:
    """Fetch inline + review comments for a single PR and return structured data."""
    repo = pr["repository"]["nameWithOwner"]
    number = pr["number"]

    # --- Inline comments ---
    inline_result = run_gh(
        ["api", f"repos/{repo}/pulls/{number}/comments", "--paginate"],
        host, check=False,
    )
    raw_inline = parse_paginated_json(inline_result.stdout) if inline_result.returncode == 0 else []
    inline_comments = []
    for c in raw_inline:
        if c.get("user", {}).get("login") != user:
            continue
        body = c.get("body", "")
        ext = get_extension(c.get("path", ""))
        inline_comments.append({
            "id": c.get("id"),
            "path": c.get("path"),
            "position": c.get("position"),
            "original_line": c.get("original_line"),
            "body": body,
            "diff_hunk": c.get("diff_hunk"),
            "created_at": c.get("created_at"),
            "side": c.get("side"),
            "file_extension": ext,
            "trivial": is_trivial(body) if body else True,
        })

    # --- Review-level comments ---
    review_result = run_gh(
        ["api", f"repos/{repo}/pulls/{number}/reviews"],
        host, check=False,
    )
    raw_reviews = parse_paginated_json(review_result.stdout) if review_result.returncode == 0 else []
    review_comments = []
    for r in raw_reviews:
        if r.get("user", {}).get("login") != user:
            continue
        body = r.get("body", "") or ""
        review_comments.append({
            "id": r.get("id"),
            "state": r.get("state"),
            "body": body,
            "submitted_at": r.get("submitted_at"),
            "trivial": is_trivial(body) if body.strip() else True,
        })

    # --- File type summary ---
    file_types: dict[str, int] = {}
    for c in inline_comments:
        ext = c["file_extension"]
        file_types[ext] = file_types.get(ext, 0) + 1

    return {
        "pr_number": number,
        "repository": repo,
        "pr_title": pr.get("title", ""),
        "pr_url": pr.get("url", ""),
        "closed_at": pr.get("closedAt", ""),
        "inline_comments": inline_comments,
        "review_comments": review_comments,
        "file_types": file_types,
    }


def cache_filename(repo: str, number: int) -> str:
    """Generate a safe cache filename for a PR."""
    safe_repo = repo.replace("/", "-")
    return f"pr-{safe_repo}-{number}.json"


# ---------------------------------------------------------------------------
# Index builder
# ---------------------------------------------------------------------------

def build_index(cache_dir: Path, user: str, host: str, display_name: str) -> dict:
    """Scan cached PR files and build index.json."""
    pr_files = sorted(cache_dir.glob("pr-*.json"))
    total_comments = 0
    repos: dict[str, dict] = {}
    pr_list = []

    for pf in pr_files:
        try:
            with open(pf) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        n_inline = len(data.get("inline_comments", []))
        n_review = len([r for r in data.get("review_comments", []) if r.get("body", "").strip()])
        count = n_inline + n_review
        total_comments += count

        repo_name = data.get("repository", "")
        if repo_name not in repos:
            repos[repo_name] = {"name": repo_name, "pr_count": 0, "comment_count": 0}
        repos[repo_name]["pr_count"] += 1
        repos[repo_name]["comment_count"] += count

        pr_list.append({
            "pr_number": data.get("pr_number"),
            "repository": repo_name,
            "file": pf.name,
            "comment_count": count,
            "closed_at": data.get("closed_at", ""),
        })

    index = {
        "username": user,
        "github_host": host,
        "display_name": display_name,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_prs_cached": len(pr_files),
        "total_comments": total_comments,
        "repositories": list(repos.values()),
        "pr_list": pr_list,
    }

    with open(cache_dir / "index.json", "w") as f:
        json.dump(index, f, indent=2)

    return index


# ---------------------------------------------------------------------------
# Display name helper
# ---------------------------------------------------------------------------

def fetch_display_name(user: str, host: str) -> str:
    """Fetch the user's display name from GitHub, falling back to username."""
    hostname_args = ["--hostname", host] if host != "github.com" else []
    result = run_gh(
        ["api", f"users/{user}", "--jq", ".name"] + hostname_args,
        host, check=False,
    )
    name = result.stdout.strip() if result.returncode == 0 else ""
    return name if name and name != "null" else user


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fetch GitHub review data for a user.")
    parser.add_argument("--user", required=True, help="GitHub username")
    parser.add_argument("--host", default=None, help="GitHub host (auto-detected if omitted)")
    parser.add_argument("--cache-dir", required=True, help="Directory to store cached PR data")
    parser.add_argument("--limit", type=int, default=150, help="Max PRs to fetch (default: 150)")
    args = parser.parse_args()

    # Resolve host
    host = args.host or detect_host()
    cache_dir = Path(args.cache_dir).expanduser().resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)

    user = args.user
    limit = args.limit

    print(f"Fetching reviews for {user} on {host}")
    print(f"Cache directory: {cache_dir}")
    print(f"Limit: {limit} PRs")
    print()

    # Check for checkpoint (resume support)
    checkpoint = load_checkpoint(cache_dir)
    if checkpoint:
        pr_list = checkpoint["pr_list"]
        start_index = checkpoint["last_index"] + 1
        print(f"Resuming from checkpoint: PR {start_index + 1}/{len(pr_list)}")
    else:
        # Search for PRs
        print("Searching for PRs reviewed by user...")
        pr_list = search_prs(user, host, limit)
        if not pr_list:
            print("No PRs found. Verify username and authentication.", file=sys.stderr)
            sys.exit(1)
        print(f"Found {len(pr_list)} PRs")
        start_index = 0

    # Fetch comments for each PR
    total = len(pr_list)
    total_inline = 0
    total_review = 0
    skipped = 0

    for i in range(start_index, total):
        pr = pr_list[i]
        repo = pr["repository"]["nameWithOwner"]
        number = pr["number"]
        fname = cache_filename(repo, number)
        fpath = cache_dir / fname

        # Skip if already cached (file exists and non-empty)
        if fpath.exists() and fpath.stat().st_size > 0:
            # Still count its comments for progress
            try:
                with open(fpath) as f:
                    cached = json.load(f)
                n_i = len(cached.get("inline_comments", []))
                n_r = len([r for r in cached.get("review_comments", []) if r.get("body", "").strip()])
                total_inline += n_i
                total_review += n_r
                print(f"  [{i + 1}/{total}] {repo}#{number} — cached ({n_i} inline, {n_r} review)")
            except (json.JSONDecodeError, OSError):
                pass  # Will re-fetch below
            else:
                continue

        # Fetch
        print(f"  [{i + 1}/{total}] {repo}#{number}...", end="", flush=True)
        try:
            data = fetch_pr_data(pr, user, host)
        except Exception as e:
            print(f" ERROR: {e}")
            skipped += 1
            continue

        n_i = len(data["inline_comments"])
        n_r = len([r for r in data["review_comments"] if r.get("body", "").strip()])
        total_inline += n_i
        total_review += n_r
        print(f" ({n_i} inline, {n_r} review)")

        # Write cache file
        with open(fpath, "w") as f:
            json.dump(data, f, indent=2)

        # Checkpoint every 10 PRs
        if (i + 1) % 10 == 0:
            save_checkpoint(cache_dir, i, pr_list)

    # Build index
    display_name = fetch_display_name(user, host)
    print()
    print("Building index...")
    index = build_index(cache_dir, user, host, display_name)
    clear_checkpoint(cache_dir)

    # Summary
    print()
    print(f"Done! Fetched {index['total_prs_cached']} PRs with {index['total_comments']} comments")
    print(f"  Inline comments: {total_inline}")
    print(f"  Review comments: {total_review}")
    if skipped:
        print(f"  Skipped (errors): {skipped}")
    print(f"  Index: {cache_dir / 'index.json'}")


if __name__ == "__main__":
    main()
