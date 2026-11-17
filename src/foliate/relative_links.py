"""Turn relative Markdown links between notes into site links.

Obsidian vaults that use "relative path to file" links, and plain Markdown
repositories, write ``[x](other.md)`` and ``[x](../folder/)``. A built page
lives at ``/folder/page/index.html``, so left alone those hrefs are dead.

The links are rewritten to ``class="wikilink"`` anchors pointing at the target
page's URL. The post-processing step already treats such anchors specially: it
turns a link to a page that is not built into plain text, and restores it when
the page appears.
"""

import posixpath
import re
from urllib.parse import unquote

from .markdown_utils import slugify_path

_ANCHOR_HREF = re.compile(r'<a href="([^"]*)"')
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def _target_page_path(href: str, page_path: str) -> tuple[str, str] | None:
    """Return (target page path, '#fragment') for a relative note link."""
    if not href or href.startswith(("#", "/", "?")) or _SCHEME.match(href):
        return None

    path_part, hash_sep, fragment = href.partition("#")
    path_part = path_part.split("?", 1)[0]
    path_part = unquote(path_part)

    is_folder = path_part.endswith("/")
    if path_part.lower().endswith(".md"):
        path_part = path_part[: -len(".md")]
    elif not is_folder:
        return None  # an asset or some other file, not a note

    base_dir = posixpath.dirname(page_path)
    target = posixpath.normpath(posixpath.join(base_dir, path_part))
    if target == "." and is_folder:
        target = ""
    if target == ".." or target.startswith("../"):
        return None  # points outside the vault
    if is_folder:
        target = posixpath.join(target, "index") if target else "index"

    return target, f"{hash_sep}{fragment}" if hash_sep else ""


def rewrite_relative_page_links(
    html: str,
    page_path: str,
    base_url: str,
    slugify: bool = False,
) -> str:
    """Rewrite relative note links in rendered HTML to wiki-style links."""

    def _replace(match: re.Match[str]) -> str:
        resolved = _target_page_path(match.group(1), page_path)
        if resolved is None:
            return match.group(0)
        target, fragment = resolved
        url_path = slugify_path(target) if slugify else target
        return f'<a class="wikilink" href="{base_url}{url_path}/{fragment}"'

    return _ANCHOR_HREF.sub(_replace, html)
