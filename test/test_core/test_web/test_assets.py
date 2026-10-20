import os
import re

from core.web.app import create_app
from core.web.assets import VERSION_LENGTH, versioned_asset_url


def test_versioned_url_appends_content_hash(tmp_path):
    (tmp_path / "page.css").write_text("body { color: red; }")

    url = versioned_asset_url(str(tmp_path), "/page.css")

    assert re.fullmatch(rf"/page\.css\?v=[0-9a-f]{{{VERSION_LENGTH}}}", url)


def test_version_is_stable_for_unchanged_file(tmp_path):
    (tmp_path / "page.css").write_text("body { color: red; }")

    first = versioned_asset_url(str(tmp_path), "/page.css")
    second = versioned_asset_url(str(tmp_path), "/page.css")

    assert first == second


def test_version_changes_when_file_changes(tmp_path):
    css = tmp_path / "page.css"
    css.write_text("body { color: red; }")
    before = versioned_asset_url(str(tmp_path), "/page.css")

    css.write_text("body { color: blue; }")
    # make sure the mtime moves even on filesystems with coarse timestamps
    stat = css.stat()
    os.utime(css, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
    after = versioned_asset_url(str(tmp_path), "/page.css")

    assert before != after


def test_version_handles_nested_paths(tmp_path):
    nested = tmp_path / "node_modules" / "lib"
    nested.mkdir(parents=True)
    (nested / "lib.js").write_text("console.log(1);")

    url = versioned_asset_url(str(tmp_path), "/node_modules/lib/lib.js")

    assert url.startswith("/node_modules/lib/lib.js?v=")


def test_missing_file_returns_plain_path(tmp_path):
    assert versioned_asset_url(str(tmp_path), "/missing.css") == "/missing.css"


def test_rendered_pages_link_versioned_css_and_js(db_path):
    app = create_app(db_path=db_path)
    app.testing = True

    html = app.test_client().get("/").get_data(as_text=True)

    assert re.search(r'href="/page\.css\?v=[0-9a-f]+"', html)
    assert re.search(r'src="/theme\.js\?v=[0-9a-f]+"', html)
    # the service worker must keep a fixed URL so it isn't re-registered as a
    # different worker on every deploy
    assert "register('/sw.js')" in html
