import html
from pathlib import Path

from build import build_site, render_inline
from readme_parser import parse_document

REPO = Path(__file__).resolve().parents[2]


def test_real_readme_builds_without_svg(tmp_path: Path) -> None:
    dist = build_site(dist=tmp_path / "dist", stars=tmp_path / "missing.json")
    page = (dist / "index.html").read_text(encoding="utf-8")
    css = (dist / "style.css").read_text(encoding="utf-8")
    script = (dist / "main.js").read_text(encoding="utf-8")
    document = parse_document(REPO / "README.md")
    for section in document.sections:
        for entry in section.entries:
            assert html.escape(entry.name) in page
    assert "Adaptive thinking is always on" in page
    assert 'src="claude55-hero.png"' in page
    assert (dist / "claude55-hero.png").read_bytes().startswith(b"\x89PNG")
    assert ".svg" not in page.lower()
    assert "<svg" not in page.lower()
    assert ".svg" not in css.lower()
    assert ".svg" not in script.lower()
    assert 'id="q"' in page
    assert "data-theme" in css
    assert "github.io/awesome-claude-5-5-agents" not in page
    hero = REPO / "assets" / "claude55-hero.png"
    assert hero.stat().st_size < 300_000
    svgs = [path for path in REPO.rglob("*.svg") if ".git" not in path.parts]
    assert svgs == []


def test_star_cache_overrides_readme_values(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# Sample List",
                "",
                "> A short tagline.",
                "",
                "## Tools",
                "",
                "- [model-bump](https://github.com/qiwei66/model-bump) - Local scanner. 1 star, MIT, last commit 2026-09-01.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    stars = tmp_path / "github_stars.json"
    stars.write_text(
        '{"repos":{"qiwei66/model-bump":{"stars":99,"license":"Apache-2.0","last_commit":"2026-09-26"}}}\n',
        encoding="utf-8",
    )
    dist = build_site(dist=tmp_path / "dist", readme=readme, stars=stars, hero=REPO / "assets" / "claude55-hero.png")
    page = (dist / "index.html").read_text(encoding="utf-8")
    assert "★ 99 stars" in page
    assert "Apache-2.0" in page
    assert "2026-09-26" in page
    assert "★ 1 star" not in page


def test_inline_code_and_links_are_escaped() -> None:
    rendered = render_inline("Use `claude-opus-5-5` and [docs](https://example.com/a).")
    assert "<code>claude-opus-5-5</code>" in rendered
    assert 'href="https://example.com/a"' in rendered
    assert "<script>" not in render_inline("not <script>alert(1)</script> here.")


def test_pages_workflow_and_gitignore() -> None:
    workflow = (REPO / ".github" / "workflows" / "website.yml").read_text(encoding="utf-8")
    assert "enablement: true" in workflow
    assert "actions/configure-pages@v5" in workflow
    assert "actions/upload-pages-artifact@v3" in workflow
    assert "actions/deploy-pages@v4" in workflow
    assert "gh-pages" not in workflow
    ignore = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "website/data/" in ignore
    assert "website/dist/" in ignore
