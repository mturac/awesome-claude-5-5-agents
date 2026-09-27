#!/usr/bin/env python3
"""Check links in README.md. Exit 0 when every http(s) link ends at HTTP 200."""

from __future__ import annotations

import ipaddress
import re
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
USER_AGENT = "awesome-claude-5-5-agents-linkcheck"
LINK_RE = re.compile(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
BLOCKED_HOSTS = {
    "localhost",
    "metadata.google.internal",
    "metadata.google.internal.",
}
MAX_REDIRECTS = 5
TIMEOUT_SECONDS = 25


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def extract_links(markdown: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in LINK_RE.finditer(markdown):
        url = match.group(1).strip()
        if url in seen:
            continue
        seen.add(url)
        found.append(url)
    return found


def ip_is_public(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def assert_public_target(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"unsupported scheme: {parsed.scheme or '(none)'}")
    if parsed.username or parsed.password:
        raise ValueError("credentials in URL")
    host = parsed.hostname
    if host is None:
        raise ValueError("missing host")
    if host.lower() in BLOCKED_HOSTS:
        raise ValueError(f"blocked host: {host}")
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None and not ip_is_public(literal):
        raise ValueError(f"blocked address: {literal}")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError(f"dns failed: {exc}") from exc
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if not ip_is_public(address):
            raise ValueError(f"blocked address: {address}")


def final_status(url: str) -> int:
    current = url
    opener = urllib.request.build_opener(NoRedirect)
    for _ in range(MAX_REDIRECTS + 1):
        assert_public_target(current)
        request = urllib.request.Request(
            current,
            method="GET",
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            },
        )
        try:
            with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
                response.read(64)
                return int(response.status)
        except urllib.error.HTTPError as exc:
            if exc.code in {301, 302, 303, 307, 308}:
                location = exc.headers.get("Location")
                if not location:
                    return int(exc.code)
                current = urllib.parse.urljoin(current, location)
                continue
            return int(exc.code)
    raise ValueError("too many redirects")


def check_readme(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    failures = 0
    for url in extract_links(text):
        if url.startswith("#"):
            slug = url[1:]
            if slug not in github_slugs(text):
                print(f"FAIL anchor {url}")
                failures += 1
            else:
                print(f"OK   anchor {url}")
            continue
        if "://" not in url:
            local = (path.parent / url).resolve()
            if local.is_file():
                print(f"OK   file   {url}")
            else:
                print(f"FAIL file   {url}")
                failures += 1
            continue
        try:
            status = final_status(url)
        except (OSError, ValueError, urllib.error.URLError) as exc:
            print(f"FAIL error  {url} ({exc})")
            failures += 1
            continue
        if status == 200:
            print(f"OK   {status} {url}")
        else:
            print(f"FAIL {status} {url}")
            failures += 1
    return failures


def github_slugs(markdown: str) -> set[str]:
    slugs: set[str] = set()
    for line in markdown.splitlines():
        if not line.startswith("#"):
            continue
        title = line.lstrip("#").strip().lower()
        title = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE)
        title = title.replace("_", "")
        slug = re.sub(r"\s+", "-", title.strip())
        slugs.add(slug)
    return slugs


def self_test() -> int:
    sample = "\n".join(
        [
            "# Migrating to 5.5",
            "- [Docs](https://example.com/a) - Text.",
            "- [Again](https://example.com/a) - Duplicate.",
            "[![Badge](https://example.com/badge.svg)](https://example.com)",
            "See [local](CONTRIBUTING.md) and [section](#migrating-to-55).",
        ]
    )
    links = extract_links(sample)
    expected = [
        "https://example.com/a",
        "https://example.com/badge.svg",
        "https://example.com",
        "CONTRIBUTING.md",
        "#migrating-to-55",
    ]
    if links != expected:
        print(f"FAIL extract {links}")
        return 1
    if "migrating-to-55" not in github_slugs(sample):
        print("FAIL slug")
        return 1
    blocked = [
        "http://127.0.0.1/",
        "http://169.254.169.254/latest/meta-data",
        "http://localhost/",
        "file:///etc/passwd",
        "http://user:secret@example.com/",
    ]
    for url in blocked:
        try:
            assert_public_target(url)
        except ValueError:
            continue
        print(f"FAIL allowed {url}")
        return 1
    print("OK   self-test")
    return 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    failures = check_readme(README)
    if failures:
        print(f"{failures} link(s) failed")
        return 1
    print("all links ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
