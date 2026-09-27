from pathlib import Path

import pytest

from readme_parser import ParseError, parse_document

REPO = Path(__file__).resolve().parents[2]
README = REPO / "README.md"


def skeleton(body: str, contents: str = "- [Tools](#tools)") -> str:
    return "\n".join(
        [
            "# Sample List",
            "",
            "> A short tagline for the sample.",
            "",
            "Intro paragraph.",
            "",
            "## Contents",
            "",
            contents,
            "",
            "## Tools",
            "",
            body,
            "",
        ]
    )


def test_real_readme_entries_and_migration_prose() -> None:
    document = parse_document(README)
    assert document.title == "Awesome Claude 5.5 Agents"
    assert document.hero_src == "assets/claude55-hero.png"
    assert "starburst" in document.hero_alt
    assert document.website_url == "https://mturac.github.io/awesome-claude-5-5-agents/"
    assert all("github.io" not in paragraph for paragraph in document.intro)
    entries = [entry for section in document.sections for entry in section.entries]
    assert len(entries) == 21
    by_name = {entry.name: entry for entry in entries}
    skill = by_name["Claude API skill"]
    assert skill.stars is None
    assert "178585 stars" in skill.description
    bump = by_name["model-bump"]
    assert bump.stars == 0
    assert bump.license == "MIT"
    assert bump.last_commit == "2026-09-24"
    assert "0 stars" not in bump.description
    quiet = by_name["lobotomized-claude-code"]
    assert quiet.stars == 121
    assert quiet.license == "no license"
    traces = by_name["vulcanbench-opus55-traces"]
    assert traces.stars == 0
    assert "86 stars" in traces.description
    migrating = next(section for section in document.sections if section.title == "Migrating to 5.5")
    assert migrating.entries == ()
    assert any("Adaptive thinking is always on" in paragraph for paragraph in migrating.paragraphs)
    assert document.closing
    assert any("waived all copyright" in paragraph for paragraph in document.closing)


def test_readme_site_address_is_not_a_markdown_link() -> None:
    text = README.read_text(encoding="utf-8")
    assert "](https://mturac.github.io/" not in text
    assert "<https://mturac.github.io/" not in text
    assert text.startswith("# Awesome Claude 5.5 Agents")


def test_malformed_star_suffix_fails(tmp_path: Path) -> None:
    path = tmp_path / "README.md"
    path.write_text(
        skeleton("- [Broken](https://example.com/broken) - Fine sentence. 4 stars, MIT, last commit yesterday."),
        encoding="utf-8",
    )
    with pytest.raises(ParseError, match="not readable"):
        parse_document(path)


def test_entry_missing_separator_fails(tmp_path: Path) -> None:
    path = tmp_path / "README.md"
    path.write_text(skeleton("- [Broken](https://example.com/broken) no separator."), encoding="utf-8")
    with pytest.raises(ParseError, match="must look like"):
        parse_document(path)


def test_contents_anchor_must_exist(tmp_path: Path) -> None:
    path = tmp_path / "README.md"
    path.write_text(
        skeleton("- [Ok](https://example.com/ok) - Fine tool.", contents="- [Missing](#missing)"),
        encoding="utf-8",
    )
    with pytest.raises(ParseError, match="has no section"):
        parse_document(path)


def test_duplicate_entry_url_fails(tmp_path: Path) -> None:
    body = "\n".join(
        [
            "- [One](https://example.com/same) - First tool.",
            "- [Two](https://example.com/same) - Second tool.",
        ]
    )
    path = tmp_path / "README.md"
    path.write_text(skeleton(body), encoding="utf-8")
    with pytest.raises(ParseError, match="duplicate entry URL"):
        parse_document(path)
