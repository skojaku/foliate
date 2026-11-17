"""Tests for relative Markdown note links."""

from foliate import build
from foliate.config import Config
from foliate.page import Page
from foliate.relative_links import rewrite_relative_page_links as rewrite


def _link(href: str, page_path: str = "compute/spiedie", slugify: bool = False):
    html = f'<p><a href="{href}">x</a></p>'
    return rewrite(html, page_path, "/wiki/", slugify)


class TestRewrite:
    def test_sibling_note(self):
        assert 'class="wikilink" href="/wiki/compute/aster/"' in _link("aster.md")

    def test_parent_directory_note(self):
        out = _link("../onboarding/start.md")
        assert 'href="/wiki/onboarding/start/"' in out

    def test_folder_link_points_at_its_index_page(self):
        assert 'href="/wiki/data/index/"' in _link("../data/")
        assert 'href="/wiki/compute/index/"' in _link("./")

    def test_fragment_is_kept(self):
        assert 'href="/wiki/compute/aster/#setup"' in _link("aster.md#setup")

    def test_percent_encoded_and_slugified(self):
        out = _link("My%20Note.md", slugify=True)
        assert 'href="/wiki/compute/My-Note/"' in out

    def test_root_page_links_stay_inside_the_vault(self):
        assert 'href="/wiki/career/"' not in _link("career/", page_path="index")
        assert 'href="/wiki/career/index/"' in _link("career/", page_path="index")

    def test_left_alone(self):
        for href in (
            "https://example.com/a.md",
            "mailto:a@b.c",
            "#section",
            "/abs/path.md",
            "figure.png",
            "../../../outside.md",
        ):
            assert _link(href) == f'<p><a href="{href}">x</a></p>'


class TestInBuild:
    def test_links_resolve_and_private_targets_become_text(self, tmp_path):
        vault = tmp_path / "vault"
        (vault / ".foliate").mkdir(parents=True)
        (vault / ".foliate" / "config.toml").write_text(
            '[build]\nhome_page = "index"\n[access]\ngated = true\n'
        )
        (vault / "sub").mkdir()
        (vault / "index.md").write_text(
            "---\ntitle: Home\n---\n[a](sub/a.md) [f](sub/) [h](sub/hidden.md)\n"
        )
        (vault / "sub" / "index.md").write_text("---\ntitle: Sub\n---\nx\n")
        (vault / "sub" / "a.md").write_text("---\ntitle: A\n---\n[up](../index.md)\n")
        (vault / "sub" / "hidden.md").write_text(
            "---\ntitle: H\npublic: false\n---\nsecret\n"
        )
        config = Config.load(vault / ".foliate" / "config.toml")
        build.build(config=config, force_rebuild=True)

        out = vault / ".foliate" / "build" / "wiki"
        home = (out / "index" / "index.html").read_text()
        assert 'href="/wiki/sub/a/"' in home
        assert 'href="/wiki/sub/index/"' in home
        assert 'href="/wiki/sub/hidden/"' not in home
        assert "wikilink-private" in home
        a = (out / "sub" / "a" / "index.html").read_text()
        assert 'href="/wiki/index/"' in a
