#!/usr/bin/env python3
"""Render the static site from README.md and the optional GitHub star cache."""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
import urllib.parse
from dataclasses import replace
from pathlib import Path

from readme_parser import Document, Entry, ParseError, Section, github_repo, parse_document

ROOT = Path(__file__).resolve().parents[1]
WEBSITE = Path(__file__).resolve().parent
README = ROOT / "README.md"
DIST = WEBSITE / "dist"
STATIC = WEBSITE / "static"
TEMPLATE = WEBSITE / "templates" / "base.html"
STARS = WEBSITE / "data" / "github_stars.json"
BLOB = "https://github.com/mturac/awesome-claude-5-5-agents/blob/main/"
DEFAULT_ALT = "Terracotta starburst and a network of agent nodes on a cream field."
LINK_OR_CODE_RE = re.compile(r"`([^`]+)`|\[([^\]]+)\]\(([^)\s]+)\)")
ANCHOR_RE = re.compile(r"#[A-Za-z0-9_-]+")


def load_stars(path: Path) -> dict[str, dict[str, object]]:
    """Load owner/repo metadata. A missing file means README values stand."""
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: unreadable JSON") from exc
    repos = data.get("repos") if isinstance(data, dict) else None
    if not isinstance(repos, dict):
        raise SystemExit(f"{path}: missing repos object")
    cleaned: dict[str, dict[str, object]] = {}
    for key, value in repos.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            raise SystemExit(f"{path}: malformed repo record")
        cleaned[key] = value
    return cleaned


def overlay(entry: Entry, repos: dict[str, dict[str, object]]) -> Entry:
    """Replace README stars when the cache has a value. None keeps the README."""
    repo = github_repo(entry.url)
    if repo is None:
        return entry
    extra = repos.get(repo)
    if not isinstance(extra, dict):
        return entry
    stars = entry.stars if extra.get("stars") is None else extra.get("stars")
    license_name = entry.license if extra.get("license") is None else extra.get("license")
    last_commit = entry.last_commit if extra.get("last_commit") is None else extra.get("last_commit")
    if stars is not None and (isinstance(stars, bool) or not isinstance(stars, int)):
        raise SystemExit(f"star cache for {repo} has a non-integer stars value")
    if license_name is not None and not isinstance(license_name, str):
        raise SystemExit(f"star cache for {repo} has a non-text license")
    if last_commit is not None and not isinstance(last_commit, str):
        raise SystemExit(f"star cache for {repo} has a non-text last commit")
    return replace(entry, stars=stars, license=license_name, last_commit=last_commit)


def externalize(url: str) -> str:
    """Turn a README link into a safe href. Relative files point at the repo."""
    if url.startswith("#"):
        if ANCHOR_RE.fullmatch(url) is None:
            raise ValueError(url)
        return url
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return url
    if parsed.scheme or url.startswith(("//", "/", "\\")) or "\\" in url:
        raise ValueError(url)
    return BLOB + urllib.parse.quote(url, safe="/")


def render_inline(text: str) -> str:
    """Escape README inline markdown (code spans and links) to HTML."""
    parts: list[str] = []
    position = 0
    for match in LINK_OR_CODE_RE.finditer(text):
        parts.append(html.escape(text[position : match.start()]))
        if match.group(1) is not None:
            parts.append(f"<code>{html.escape(match.group(1))}</code>")
        else:
            label = html.escape(match.group(2))
            href = html.escape(externalize(match.group(3)), quote=True)
            if href.startswith("#"):
                parts.append(f'<a href="{href}">{label}</a>')
            else:
                parts.append(f'<a href="{href}" rel="noopener noreferrer">{label}</a>')
        position = match.end()
    parts.append(html.escape(text[position:]))
    return "".join(parts)


def plain_text(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        if match.group(1) is not None:
            return match.group(1)
        return match.group(2)

    return LINK_OR_CODE_RE.sub(replace, text).replace("`", "")


def render_paragraphs(paragraphs: tuple[str, ...]) -> str:
    blocks: list[str] = []
    for paragraph in paragraphs:
        image = re.fullmatch(r"\[!\[([^\]]*)\]\(([^)\s]+)\)\]\(([^)\s]+)\)", paragraph)
        if image:
            alt = html.escape(image.group(1), quote=True)
            src = html.escape(externalize(image.group(2)), quote=True)
            href = html.escape(externalize(image.group(3)), quote=True)
            blocks.append(f'<p class="badge"><a href="{href}" rel="noopener noreferrer"><img src="{src}" alt="{alt}"></a></p>')
            continue
        blocks.append(f"<p>{render_inline(paragraph)}</p>")
    return "".join(blocks)


def meta_html(entry: Entry) -> str:
    chips: list[str] = []
    if entry.stars is not None:
        label = "star" if entry.stars == 1 else "stars"
        chips.append(f"★ {entry.stars:,} cumulative GitHub {label}")
    if entry.license:
        chips.append("No license" if entry.license.lower() == "no license" else entry.license)
    if entry.last_commit:
        chips.append(entry.last_commit)
    if not chips:
        chips.append("Docs")
    inner = "".join(f"<span>{html.escape(chip)}</span>" for chip in chips)
    return f'<p class="meta">{inner}</p>'


def render_entry(entry: Entry, section: Section) -> str:
    hay = " ".join(
        [
            entry.name,
            plain_text(entry.description),
            entry.url,
            entry.license or "",
            entry.last_commit or "",
            section.title,
        ]
    )
    bits = [
        f'<article class="card" data-entry="{html.escape(hay.lower(), quote=True)}">',
        f'<h3><a href="{html.escape(externalize(entry.url), quote=True)}" rel="noopener noreferrer">{html.escape(entry.name)}</a></h3>',
        f'<p class="desc">{render_inline(entry.description)}</p>',
        meta_html(entry),
        "</article>",
    ]
    return "".join(bits)


def render_section(section: Section) -> str:
    if section.title == "Contents":
        return ""
    kind = "entries" if section.entries else "prose"
    text = plain_text(" ".join(section.paragraphs))
    parts = [
        f'<section id="{html.escape(section.slug, quote=True)}" data-section="{kind}" data-text="{html.escape(text.lower(), quote=True)}">',
        "<h2>" + html.escape(section.title),
    ]
    if section.entries:
        parts.append(f' <span class="tally">{len(section.entries)}</span>')
    parts.append("</h2>")
    if section.paragraphs:
        wrapper = "prose" if kind == "prose" else "section-note"
        parts.append(f'<div class="{wrapper}">{render_paragraphs(section.paragraphs)}</div>')
    if section.entries:
        parts.append('<div class="cards">')
        parts.extend(render_entry(entry, section) for entry in section.entries)
        parts.append("</div>")
    parts.append("</section>")
    return "".join(parts)


def render_nav(document: Document) -> str:
    links = []
    for section in document.sections:
        if section.title == "Contents":
            continue
        links.append(f'<a href="#{html.escape(section.slug, quote=True)}">{html.escape(section.title)}</a>')
    return "".join(links)


def fill(template: str, slots: dict[str, str]) -> str:
    for key, value in slots.items():
        token = f"@@{key}@@"
        if token not in template:
            raise SystemExit(f"template is missing {token}")
        template = template.replace(token, value)
    leftover = re.findall(r"@@[A-Z_]+@@", template)
    if leftover:
        raise SystemExit(f"unfilled template slots: {leftover}")
    return template


def visible_sections(document: Document, repos: dict[str, dict[str, object]]) -> Document:
    sections: list[Section] = []
    for section in document.sections:
        sections.append(
            Section(
                title=section.title,
                slug=section.slug,
                line=section.line,
                paragraphs=section.paragraphs,
                entries=tuple(overlay(entry, repos) for entry in section.entries),
                toc=section.toc,
            )
        )
    return replace(document, sections=tuple(sections))


def build_site(
    dist: Path | None = None,
    readme: Path | None = None,
    stars: Path | None = None,
    hero: Path | None = None,
) -> Path:
    """Write the site to dist and return that directory."""
    readme_path = README if readme is None else readme
    out = DIST if dist is None else dist
    document = visible_sections(parse_document(readme_path), load_stars(STARS if stars is None else stars))
    if document.hero_src:
        hero_path = (readme_path.parent / document.hero_src).resolve()
    else:
        hero_path = hero
    if hero_path is None or not hero_path.is_file():
        raise SystemExit("hero image is missing")
    if hero_path.suffix.lower() != ".png" or not hero_path.read_bytes().startswith(b"\x89PNG"):
        raise SystemExit("hero image must be a PNG")
    alt = document.hero_alt or DEFAULT_ALT
    total = sum(len(section.entries) for section in document.sections)
    main = ['<div class="lede">', render_paragraphs(document.intro), "</div>"]
    main.append('<p id="empty" hidden>Nothing in the list matches that search.</p>')
    main.extend(render_section(section) for section in document.sections)
    closing = render_paragraphs(document.closing)
    closing += '<p class="colophon">Rendered from README.md.</p>'
    template = TEMPLATE.read_text(encoding="utf-8")
    page = fill(
        template,
        {
            "TITLE": html.escape(document.title),
            "TAGLINE": html.escape(document.tagline),
            "HERO_ALT": html.escape(alt, quote=True),
            "COUNT": html.escape(f"{total} entries"),
            "NAV": render_nav(document),
            "MAIN": "".join(main),
            "CLOSING": closing,
        },
    )
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for asset in STATIC.iterdir():
        if asset.suffix.lower() == ".svg" or asset.name.lower().endswith(".svg"):
            raise SystemExit(f"refusing SVG asset {asset.name}")
        shutil.copy2(asset, out / asset.name)
    shutil.copy2(hero_path, out / "claude55-hero.png")
    (out / "index.html").write_text(page, encoding="utf-8")
    return out


def main() -> int:
    try:
        out = build_site()
    except ParseError as exc:
        print(exc, file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"refusing URL: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {out / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
