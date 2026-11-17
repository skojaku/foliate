"""Tests for the gated-site mode ([access] gated = true)."""

import json

import pytest

from foliate import build
from foliate.config import Config
from foliate.deploy import deploy_github_pages
from foliate.page import Page, is_public_meta, is_published_meta


def _make_vault(tmp_path, gated: bool):
    vault = tmp_path / "vault"
    foliate_dir = vault / ".foliate"
    foliate_dir.mkdir(parents=True)
    access = "\n[access]\ngated = true\n" if gated else ""
    config_path = foliate_dir / "config.toml"
    config_path.write_text(
        '[site]\nname = "Lab"\nurl = "https://lab.example.com"\n'
        '\n[build]\nhome_page = "Home"\n' + access
    )
    # No frontmatter flags at all: the common case for a lab wiki.
    (vault / "Home.md").write_text("---\ntitle: Home\n---\n\nWelcome.\n")
    (vault / "Plain.md").write_text("---\ntitle: Plain\n---\n\nNo flags.\n")
    (vault / "Hidden.md").write_text(
        "---\ntitle: Hidden\npublic: false\n---\n\nStay out.\n"
    )
    (vault / "Unlisted.md").write_text(
        "---\ntitle: Unlisted\npublished: false\n---\n\nBuilt, not listed.\n"
    )
    return vault, Config.load(config_path)


class TestVisibilityHelpers:
    def test_ordinary_site_requires_public_true(self):
        assert is_public_meta({}) is False
        assert is_public_meta({"public": None}) is False
        assert is_public_meta({"public": True}) is True
        assert is_published_meta({}) is False
        assert is_published_meta({"published": "2026-01-01"}) is True

    def test_gated_site_builds_everything_unless_public_false(self):
        assert is_public_meta({}, gated=True) is True
        assert is_public_meta({"public": None}, gated=True) is True
        assert is_public_meta({"public": True}, gated=True) is True
        assert is_public_meta({"public": False}, gated=True) is False

    def test_gated_site_lists_everything_unless_published_false(self):
        assert is_published_meta({}, gated=True) is True
        assert is_published_meta({"published": "2026-01-01"}, gated=True) is True
        assert is_published_meta({"published": False}, gated=True) is False

    def test_page_is_published_follows_gate(self):
        plain = Page.from_markdown("a", {}, "x", render_html=False)
        gated = Page.from_markdown("a", {}, "x", render_html=False, gated=True)
        assert plain.is_published is False
        assert gated.is_published is True


class TestAccessConfig:
    def test_gated_defaults_to_false(self, tmp_path):
        config = Config.load(tmp_path / ".foliate" / "config.toml")
        assert config.access.gated is False

    def test_gated_loads_from_toml(self, tmp_path):
        _, config = _make_vault(tmp_path, gated=True)
        assert config.access.gated is True
        assert config.to_template_context()["gated"] is True

    def test_gated_must_be_a_bool(self, tmp_path):
        foliate_dir = tmp_path / ".foliate"
        foliate_dir.mkdir()
        path = foliate_dir / "config.toml"
        path.write_text('[access]\ngated = "yes"\n')
        with pytest.raises(TypeError, match="must be a boolean"):
            Config.load(path)


class TestGatedBuild:
    def test_ordinary_site_skips_pages_without_public(self, tmp_path):
        vault, config = _make_vault(tmp_path, gated=False)
        build.build(config=config, force_rebuild=True)
        out = vault / ".foliate" / "build" / "wiki"
        assert not (out / "Plain" / "index.html").exists()
        assert not (vault / ".foliate" / "build" / "robots.txt").exists()

    def test_gated_site_builds_pages_without_flags(self, tmp_path):
        vault, config = _make_vault(tmp_path, gated=True)
        build.build(config=config, force_rebuild=True)
        out = vault / ".foliate" / "build" / "wiki"
        assert (out / "Home" / "index.html").exists()
        assert (out / "Plain" / "index.html").exists()
        assert (out / "Unlisted" / "index.html").exists()
        assert not (out / "Hidden" / "index.html").exists()

    def test_gated_site_lists_pages_in_search_but_not_unlisted(self, tmp_path):
        vault, config = _make_vault(tmp_path, gated=True)
        build.build(config=config, force_rebuild=True)
        search = json.loads(
            (vault / ".foliate" / "build" / "wiki" / "search.json").read_text()
        )
        titles = {entry["title"] for entry in search}
        assert {"Home", "Plain"} <= titles
        assert "Unlisted" not in titles
        assert "Hidden" not in titles

    def test_gated_site_tells_crawlers_to_stay_away(self, tmp_path):
        vault, config = _make_vault(tmp_path, gated=True)
        build.build(config=config, force_rebuild=True)
        build_dir = vault / ".foliate" / "build"
        assert "Disallow: /" in (build_dir / "robots.txt").read_text()
        html = (build_dir / "wiki" / "Plain" / "index.html").read_text()
        assert '<meta name="robots" content="noindex, nofollow">' in html

    def test_ordinary_site_has_no_noindex(self, tmp_path):
        vault, config = _make_vault(tmp_path, gated=False)
        (vault / "Plain.md").write_text("---\ntitle: Plain\npublic: true\n---\n\nx\n")
        build.build(config=config, force_rebuild=True)
        html = (
            vault / ".foliate" / "build" / "wiki" / "Plain" / "index.html"
        ).read_text()
        assert "noindex" not in html

    def test_turning_the_gate_on_rebuilds_cached_private_pages(self, tmp_path):
        """A cached 'private' verdict must not outlive a config change."""
        vault, config = _make_vault(tmp_path, gated=False)
        build.build(config=config, force_rebuild=False)
        out = vault / ".foliate" / "build" / "wiki" / "Plain" / "index.html"
        assert not out.exists()

        config_path = vault / ".foliate" / "config.toml"
        config_path.write_text(config_path.read_text() + "\n[access]\ngated = true\n")
        config = Config.load(config_path)
        build.build(config=config, force_rebuild=False)
        assert out.exists()


class TestGatedDeploy:
    def test_github_pages_deploy_is_refused(self, tmp_path, capsys):
        vault, config = _make_vault(tmp_path, gated=True)
        target = tmp_path / "pages"
        (target / ".git").mkdir(parents=True)
        config.deploy.target = str(target)
        build.build(config=config, force_rebuild=True)

        assert deploy_github_pages(config) is False
        assert "gated" in capsys.readouterr().err
