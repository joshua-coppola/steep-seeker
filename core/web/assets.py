import hashlib
import mimetypes
import os
from functools import lru_cache

# hex characters of the content hash kept in ?v=; plenty to make collisions
# between two versions of the same file a non-issue
VERSION_LENGTH = 10


def register_static_mimetypes() -> None:
    """
    Flask picks a static file's Content-Type from Python's mimetypes table,
    which falls back to the OS's /etc/mime.types for anything it doesn't know.
    Python < 3.13 has no built-in .webp entry and the slim Docker image has no
    /etc/mime.types, so without this the manifest screenshots are served as
    application/octet-stream and installers (e.g. PWABuilder) reject them.
    """
    mimetypes.add_type("image/webp", ".webp")


register_static_mimetypes()


@lru_cache(maxsize=256)
def _content_hash(file_path: str, mtime_ns: int) -> str:
    """
    Hash of a static file's contents. Cached per (path, mtime) so each file is
    only read once per change rather than on every page render; mtime_ns is
    only part of the cache key, so an edited file gets rehashed.
    """
    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()[:VERSION_LENGTH]


def versioned_asset_url(static_folder: str, path: str) -> str:
    """
    path (a site-root URL like "/page.css") with ?v=<content hash> appended,
    so browsers and the service worker fetch a fresh copy whenever the file
    changes instead of serving a stale cached one. Files that don't exist are
    returned unversioned rather than breaking the page render.
    """
    file_path = os.path.join(static_folder, path.lstrip("/"))
    try:
        mtime_ns = os.stat(file_path).st_mtime_ns
    except OSError:
        return path
    return f"{path}?v={_content_hash(file_path, mtime_ns)}"
