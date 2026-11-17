"""Tests for the per-page "edit this page" link ([edit] url)."""

import pytest

from foliate import build
from foliate.config import Config


def _vault(tmp_path, edit_toml: str, wiki_prefix: str = "wiki"):
    vault = tmp_path / "vault"
    (vault / ".foliate").mkdir(parents=True)
    (vault / ".foliate" / "config.toml").write_text(
        f'[build]\nwiki_prefix = "{wiki_prefix}"\nhome_page = "Home"\n'
        "[access]\ngated = true\n" + edit_toml
    )
    (vault / "Home.md").write_text("---\ntitle: Home\n---\nhi\n")
    (vault / "sub dir").mkdir()
    (vault / "sub dir" / "Note.md").write_text("---\ntitle: Note\n---\nx\n")
    return vault, Config.load(vault / ".foliate" / "config.toml")


def _html(vault, *parts):
    return (vault / ".foliate" / "build" / "/".join(parts) / "index.html").read_text()


class TestEditLink:
    def test_link_points_at_the_source_file(self, tmp_path):
        vault, config = _vault(
            tmp_path,
            '[edit]\nurl = "https://github.com/o/r/edit/main/wiki/{path}"\n',
        )
        build.build(config=config, force_rebuild=True)
        html = _html(vault, "wiki", "sub dir", "Note")
        assert 'href="https://github.com/o/r/edit/main/wiki/sub%20dir/Note.md"' in html
        assert "Edit this page" in html

    def test_label_is_configurable(self, tmp_path):
        vault, config = _vault(
            tmp_path,
            '[edit]\nurl = "https://x/{path}"\nlabel = "Edit on GitHub"\n',
        )
        build.build(config=config, force_rebuild=True)
        assert "Edit on GitHub" in _html(vault, "wiki", "Home")

    def test_link_shows_when_the_wiki_is_at_the_site_root(self, tmp_path):
        vault, config = _vault(tmp_path, '[edit]\nurl = "https://x/{path}"\n', "")
        build.build(config=config, force_rebuild=True)
        assert 'href="https://x/Home.md"' in _html(vault, "Home")

    def test_no_link_without_a_url(self, tmp_path):
        vault, config = _vault(tmp_path, "")
        build.build(config=config, force_rebuild=True)
        assert "Edit this page" not in _html(vault, "wiki", "Home")

    def test_cached_pages_keep_the_link_after_a_rebuild(self, tmp_path):
        vault, config = _vault(tmp_path, '[edit]\nurl = "https://x/{path}"\n')
        build.build(config=config, force_rebuild=True)
        build.build(config=config, force_rebuild=False)
        assert 'href="https://x/Home.md"' in _html(vault, "wiki", "Home")

    def test_url_needs_the_path_placeholder(self, tmp_path):
        foliate_dir = tmp_path / ".foliate"
        foliate_dir.mkdir()
        path = foliate_dir / "config.toml"
        path.write_text('[edit]\nurl = "https://github.com/o/r"\n')
        with pytest.raises(ValueError, match="must contain"):
            Config.load(path)
