#!/usr/bin/env python3
"""Refresh GitHub stars, SPDX ids, and last-commit dates for README entries.

Reads GITHUB_TOKEN from the environment (the Actions token in CI). The token
is sent only as an Authorization header to api.github.com and is never written
to disk. When the token is missing or a repo request fails, that entry keeps
the stars, license, and last-commit text already parsed from README.md.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from readme_parser import ParseError, github_repo, parse_document

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
DATA_PATH = Path(__file__).resolve().parent / "data" / "github_stars.json"
API = "https://api.github.com"
USER_AGENT = "awesome-claude-5-5-agents-website"
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


class FetchError(Exception):
    """One GitHub API call failed. The caller keeps the README values."""


def build_request(url: str, token: str) -> urllib.request.Request:
    """Build a GitHub API request. The token stays in the header."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "api.github.com":
        raise FetchError("refusing a non-GitHub API URL")
    if token and token in url:
        raise FetchError("refusing to put the token in the URL")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers)


def default_transport(url: str, token: str) -> object:
    """GET JSON from the GitHub API."""
    request = build_request(url, token)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise FetchError(f"HTTP {exc.code} for {urllib.parse.urlparse(url).path}") from exc
    except urllib.error.URLError as exc:
        raise FetchError(f"request failed for {urllib.parse.urlparse(url).path}") from exc
    except json.JSONDecodeError as exc:
        raise FetchError("GitHub returned unreadable JSON") from exc


def _last_commit(commits: object) -> str | None:
    if not isinstance(commits, list) or not commits:
        return None
    first = commits[0]
    if not isinstance(first, dict):
        return None
    commit = first.get("commit")
    if not isinstance(commit, dict):
        return None
    committer = commit.get("committer")
    if not isinstance(committer, dict):
        return None
    date = committer.get("date")
    if not isinstance(date, str) or len(date) < 10:
        return None
    day = date[:10]
    if DATE_RE.fullmatch(day) is None:
        return None
    return day


def normalize(info: object, commits: object) -> dict[str, object]:
    """Turn repo and commit payloads into stars, license, and last commit."""
    if not isinstance(info, dict):
        raise FetchError("repo payload was not an object")
    stars = info.get("stargazers_count")
    if isinstance(stars, bool) or not isinstance(stars, int):
        raise FetchError("stargazers_count missing")
    license_name = "no license"
    license_info = info.get("license")
    if isinstance(license_info, dict):
        spdx = license_info.get("spdx_id")
        if isinstance(spdx, str) and spdx and spdx != "NOASSERTION":
            license_name = spdx
    return {"stars": stars, "license": license_name, "last_commit": _last_commit(commits)}


def enrich(urls: list[str], *, token: str, transport: object) -> dict[str, dict[str, object]]:
    """Fetch metadata for GitHub entry URLs. Failed repos are omitted."""
    if not token:
        return {}
    if not callable(transport):
        raise TypeError("transport must be callable")
    repos: list[str] = []
    for url in urls:
        repo = github_repo(url)
        if repo and repo not in repos:
            repos.append(repo)
    found: dict[str, dict[str, object]] = {}
    for repo in repos:
        owner, name = repo.split("/", 1)
        owner_q = urllib.parse.quote(owner)
        name_q = urllib.parse.quote(name)
        info_url = f"{API}/repos/{owner_q}/{name_q}"
        commit_url = f"{API}/repos/{owner_q}/{name_q}/commits?per_page=1"
        try:
            info = transport(info_url, token)
            commits = transport(commit_url, token)
            found[repo] = normalize(info, commits)
        except (FetchError, KeyError, TypeError, ValueError) as exc:
            print(f"fallback: kept README values for {repo} ({exc})", file=sys.stderr)
    return found


def write_cache(path: Path, repos: dict[str, dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"repos": repos}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def entry_urls(readme: Path) -> list[str]:
    document = parse_document(readme)
    return [entry.url for section in document.sections for entry in section.entries]


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    try:
        urls = entry_urls(README)
    except ParseError as exc:
        print(exc, file=sys.stderr)
        return 1
    if not token:
        print("GITHUB_TOKEN is unset; star fetch skipped and the site will use README values.")
        return 0
    repos = enrich(urls, token=token, transport=default_transport)
    write_cache(DATA_PATH, repos)
    print(f"Wrote {len(repos)} repo records to {DATA_PATH.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
