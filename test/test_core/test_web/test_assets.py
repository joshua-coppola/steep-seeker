import json
import mimetypes
import os
import re

from core.web.app import create_app
from core.web.assets import (
    VERSION_LENGTH,
    register_static_mimetypes,
    versioned_asset_url,
)


def test_webp_mimetype_registered_without_system_mime_types(monkeypatch):
    # the slim Docker image has no /etc/mime.types, leaving only Python's
    # built-in table, which (before 3.13) has no .webp entry
    monkeypatch.setattr(mimetypes, "_db", mimetypes.MimeTypes(filenames=()))
    monkeypatch.setattr(mimetypes, "inited", True)

    register_static_mimetypes()

    assert mimetypes.guess_type("screenshot.webp")[0] == "image/webp"


def test_assetlinks_served_from_well_known(db_path):
    # Android checks exactly this path to verify the Play Store app (a Trusted
    # Web Activity) belongs to this site; anywhere else it shows a browser bar
    app = create_app(db_path=db_path)
    app.testing = True

    response = app.test_client().get("/.well-known/assetlinks.json")

    assert response.status_code == 200
    assert response.mimetype == "application/json"
    statement = response.get_json()[0]
    assert statement["relation"] == ["delegate_permission/common.handle_all_urls"]
    assert statement["target"]["namespace"] == "android_app"


def test_manifest_screenshots_served_as_images(db_path):
    app = create_app(db_path=db_path)
    app.testing = True
    client = app.test_client()
    with open(os.path.join(app.static_folder, "manifest.json")) as f:
        screenshots = json.load(f)["screenshots"]

    assert screenshots
    for screenshot in screenshots:
        response = client.get(screenshot["src"])
        assert response.status_code == 200, screenshot["src"]
        assert response.mimetype == screenshot["type"], screenshot["src"]


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
