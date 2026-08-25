from flask import Flask

from core.connectors.database import DATABASE_PATH
from core.web.management_routes import management_web
from core.web.management_routes import nav_links as management_nav_links
from core.web.routes import web


def create_management_app(db_path: str = DATABASE_PATH) -> Flask:
    """
    Application factory for the admin/management app. Deliberately kept
    separate from core.web.app.create_app (which app_new.py runs) so
    management routes are never exposed on whatever serves the public
    site -- this has its own entry point (management_new.py) instead.

    Also registers the public blueprint so links from a management page
    (e.g. the add-resort redirect to /interactive-map) resolve.
    """
    app = Flask(
        __name__,
        static_url_path="",
        static_folder="../../static",
        template_folder="../../templates",
    )
    app.config["DATABASE_PATH"] = db_path
    app.register_blueprint(web)
    app.register_blueprint(management_web)

    @app.context_processor
    def inject_nav_links():
        # every page rendered by this app instance -- public routes
        # included -- gets the Management link too, since you have access
        # to it in this instance
        return {"nav_links": management_nav_links}

    return app
