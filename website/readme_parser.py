"""Parse README.md into sections and entries.

The list file is the source of truth. Entry bullets that do not match the
awesome list shape, or that end with an unreadable star suffix, raise
ParseError instead of being skipped.
"""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
REPO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
ENTRY_RE = re.compile(r"^- \[(?P<name>[^\]]+)\]\((?P<url>[^)\s]+)\) - (?P<description>\S.*)$")
TOC_RE = re.compile(r"^- \[(?P<name>[^\]]+)\]\(#(?P<slug>[A-Za-z0-9_-]+)\)$")
IMAGE_RE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<src>[^)\s]+)\)$")
IMAGE_LINK_RE = re.compile(r"^\[!\[(?P<alt>[^\]]*)\]\((?P<src>[^)\s]+)\)\]\((?P<href>[^)\s]+)\)$")
WEBSITE_LINE_RE = re.compile(r"^Website:\s+(?P<url>https://\S+)\s*$")
META_TAIL_RE = re.compile(r"(?P<stars>\d+) stars?, (?P<license>[^,]+), last commit (?P<date>\d{4}-\d{2}-\d{2})\.")
SLUG_PUNCT_RE = re.compile(r"[^\w\s-]", flags=re.UNICODE)


class ParseError(Exception):
    """README.md could not be parsed. The message includes the line number."""

    def __init__(self, line: int, message: str, path: Path | None = None) -> None:
        self.line = line
        name = path.name if path is not None else "README.md"
        super().__init__(f"{name}:{line}: {message}")


@dataclass(frozen=True)
class Entry:
    name: str
    url: str
    description: str
    stars: int | None
    license: str | None
    last_commit: str | None
    line: int


@dataclass(frozen=True)
class TocItem:
    name: str
    slug: str
    line: int


@dataclass(frozen=True)
class Section:
    title: str
    slug: str
    line: int
    paragraphs: tuple[str, ...]
    entries: tuple[Entry, ...]
    toc: tuple[TocItem, ...]


@dataclass(frozen=True)
class Document:
    title: str
    tagline: str
    intro: tuple[str, ...]
    hero_alt: str
    hero_src: str
    website_url: str
    sections: tuple[Section, ...]
    closing: tuple[str, ...]


def github_slug(title: str) -> str:
    """Match GitHub heading anchors and scripts/link-check.py.

    Punctuation is removed and each remaining space becomes its own hyphen.
    "Video & Creative" is therefore video--creative, the same slug awesome-lint
    and GitHub generate. Collapsing the double space would point the contents
    link at an anchor that does not exist.
    """
    text = SLUG_PUNCT_RE.sub("", title.lower())
    text = text.replace("_", "")
    return text.strip().replace(" ", "-")


def github_repo(url: str) -> str | None:
    """Return owner/repo when url is a GitHub repository root, else None."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != "github.com":
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2:
        return None
    owner, name = parts
    if name.endswith(".git"):
        name = name[:-4]
    if not OWNER_RE.fullmatch(owner) or not REPO_RE.fullmatch(name):
        return None
    if name in {".", ".."} or ".." in name:
        return None
    return f"{owner}/{name}"


def _check_url(url: str, line: int, path: Path) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme in {"http", "https"}:
        return
    if parsed.scheme == "" and url.startswith("#"):
        return
    if parsed.scheme == "" and not url.startswith(("//", "/", "\\")):
        return
    raise ParseError(line, f"unsupported URL {url}", path)


def _split_meta(description: str, line: int, path: Path) -> tuple[str, int | None, str | None, str | None]:
    if not description.endswith("."):
        raise ParseError(line, "description must end with a period", path)
    if META_TAIL_RE.fullmatch(description):
        raise ParseError(line, "description is only a star, license, and last-commit suffix", path)
    head, separator, tail = description.rpartition(". ")
    if separator and re.match(r"\d+ stars?,", tail):
        matched = META_TAIL_RE.fullmatch(tail)
        if matched is None:
            raise ParseError(line, "star, license, and last-commit suffix is not readable", path)
        if not head.strip():
            raise ParseError(line, "description is empty once the star suffix is removed", path)
        license_name = matched.group("license").strip()
        if not license_name:
            raise ParseError(line, "license suffix is empty", path)
        return head + ".", int(matched.group("stars")), license_name, matched.group("date")
    return description, None, None, None


def _parse_entry(line: str, lineno: int, path: Path) -> Entry:
    matched = ENTRY_RE.match(line)
    if matched is None:
        if TOC_RE.match(line):
            raise ParseError(lineno, "entry is missing a description", path)
        raise ParseError(lineno, "entry must look like '- [Name](url) - Description.'", path)
    name = matched.group("name").strip()
    url = matched.group("url").strip()
    if not name:
        raise ParseError(lineno, "entry name is empty", path)
    if url.startswith("#"):
        raise ParseError(lineno, "entry URL must be a page, not an anchor", path)
    _check_url(url, lineno, path)
    description, stars, license_name, last_commit = _split_meta(matched.group("description").strip(), lineno, path)
    return Entry(
        name=name,
        url=url,
        description=description,
        stars=stars,
        license=license_name,
        last_commit=last_commit,
        line=lineno,
    )


def _parse_title(text: str, path: Path) -> str:
    title = re.sub(r"\s*\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)\s*", " ", text)
    title = re.sub(r"\s+", " ", title).strip()
    if not title:
        raise ParseError(1, "title is empty", path)
    return title


def parse_document(path: Path) -> Document:
    """Parse an awesome-list README. Raises ParseError on a malformed entry."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ParseError(1, "the first line must be the title", path)
    title = _parse_title(lines[0][2:].strip(), path)

    tagline_parts: list[str] = []
    intro: list[str] = []
    hero_alt = ""
    hero_src = ""
    website_url = ""
    sections: list[Section] = []
    closing: list[str] = []
    current_title: str | None = None
    current_line = 0
    paragraphs: list[str] = []
    entries: list[Entry] = []
    toc: list[TocItem] = []
    seen_urls: set[str] = set()
    index = 1

    def finish_section() -> None:
        if current_title is None:
            return
        sections.append(
            Section(
                title=current_title,
                slug=github_slug(current_title),
                line=current_line,
                paragraphs=tuple(paragraphs),
                entries=tuple(entries),
                toc=tuple(toc),
            )
        )

    def take_paragraph(text: str) -> None:
        if current_title is None:
            intro.append(text)
        else:
            paragraphs.append(text)

    while index < len(lines):
        raw = lines[index]
        lineno = index + 1
        line = raw.rstrip()
        index += 1
        if line.startswith("###"):
            raise ParseError(lineno, "only a title and section headings are supported", path)
        if line.startswith("## "):
            finish_section()
            current_title = line[3:].strip()
            if not current_title:
                raise ParseError(lineno, "section heading is empty", path)
            current_line = lineno
            paragraphs = []
            entries = []
            toc = []
            continue
        if not line.strip():
            continue
        if line.startswith(">"):
            quote = line.lstrip(">").strip()
            if current_title is not None:
                take_paragraph(quote)
                continue
            tagline_parts.append(quote)
            continue
        stripped = line.strip()
        if current_title is None and WEBSITE_LINE_RE.match(stripped):
            if website_url:
                raise ParseError(lineno, "website line is repeated", path)
            matched = WEBSITE_LINE_RE.match(stripped)
            if matched is None:
                raise ParseError(lineno, "website line is not readable", path)
            website_url = matched.group("url")
            continue
        if current_title is None and IMAGE_RE.match(stripped):
            if hero_src:
                raise ParseError(lineno, "only one hero image is supported", path)
            image = IMAGE_RE.match(stripped)
            assert image is not None
            hero_alt = image.group("alt").strip()
            hero_src = image.group("src").strip()
            if not hero_alt:
                raise ParseError(lineno, "hero image needs alt text", path)
            continue
        if line.startswith("- "):
            if current_title is None:
                raise ParseError(lineno, "list item is outside a section", path)
            if current_title == "Contents":
                item = TOC_RE.match(line)
                if item is None:
                    raise ParseError(lineno, "contents item must be a markdown anchor link", path)
                toc.append(TocItem(name=item.group("name").strip(), slug=item.group("slug"), line=lineno))
                continue
            entry = _parse_entry(line, lineno, path)
            if entry.url in seen_urls:
                raise ParseError(lineno, f"duplicate entry URL {entry.url}", path)
            seen_urls.add(entry.url)
            if index < len(lines):
                nxt = lines[index]
                if nxt.strip() and not nxt.startswith("- ") and not nxt.startswith("#"):
                    raise ParseError(lineno, "entry must stay on one line", path)
            entries.append(entry)
            continue
        if line.startswith(" ") or line.startswith("\t"):
            raise ParseError(lineno, "indented list item is not an entry", path)
        block = [stripped]
        while index < len(lines):
            nxt = lines[index]
            if not nxt.strip() or nxt.startswith(("#", "-", ">")) or nxt.startswith(" ") or nxt.startswith("\t"):
                break
            block.append(nxt.strip())
            index += 1
        take_paragraph(" ".join(block))

    finish_section()
    if current_title is not None:
        # Lines after the last heading were stored on that section. Closing
        # copy in this README is the license note, which has no heading.
        pass

    # Re-read trailing license lines: they were attached to the last section
    # only if they appeared before the next heading. There is no heading after
    # Contributing, so those paragraphs landed on that section. Split a
    # trailing image-link or waiver off Contributing when it is not the
    # section's own prose. The Contributing section's own paragraph stays.
    if sections and sections[-1].title == "Contributing":
        kept: list[str] = []
        for paragraph in sections[-1].paragraphs:
            if IMAGE_LINK_RE.match(paragraph) or paragraph.startswith("To the extent possible under law"):
                closing.append(paragraph)
            else:
                kept.append(paragraph)
        last = sections[-1]
        sections[-1] = Section(
            title=last.title,
            slug=last.slug,
            line=last.line,
            paragraphs=tuple(kept),
            entries=last.entries,
            toc=last.toc,
        )

    by_slug = {section.slug: section for section in sections}
    if len(by_slug) != len(sections):
        raise ParseError(1, "two sections produce the same anchor", path)
    for section in sections:
        if section.title != "Contents":
            continue
        seen_slugs: set[str] = set()
        for item in section.toc:
            if item.slug in seen_slugs:
                raise ParseError(item.line, f"duplicate contents anchor #{item.slug}", path)
            seen_slugs.add(item.slug)
            if item.slug not in by_slug:
                raise ParseError(item.line, f"contents anchor #{item.slug} has no section", path)

    if not tagline_parts:
        raise ParseError(1, "tagline blockquote is missing", path)
    if not any(section.entries for section in sections):
        raise ParseError(1, "README has no entries", path)

    return Document(
        title=title,
        tagline=" ".join(tagline_parts),
        intro=tuple(intro),
        hero_alt=hero_alt,
        hero_src=hero_src,
        website_url=website_url,
        sections=tuple(sections),
        closing=tuple(closing),
    )
