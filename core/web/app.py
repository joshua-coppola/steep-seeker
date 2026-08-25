from flask import Flask

from core.connectors.database import DATABASE_PATH
from core.web.routes import nav_links, web


def create_app(db_path: str = DATABASE_PATH) -> Flask:
    """
    Application factory for the Flask app. db_path is overridable so tests
    can point routes at a temporary database instead of the real one.
    """
    app = Flask(
        __name__,
        static_url_path="",
        static_folder="../../static",
        template_folder="../../templates",
    )
    app.config["DATABASE_PATH"] = db_path
    app.register_blueprint(web)

    @app.context_processor
    def inject_nav_links():
        # every page rendered by this app instance gets the same nav,
        # rather than each route having to pass it explicitly
        return {"nav_links": nav_links}

    return app
