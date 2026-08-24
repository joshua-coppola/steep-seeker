from flask import Flask

from core.web.routes import web


def create_app() -> Flask:
    """
    Application factory for the Flask app
    """
    app = Flask(
        __name__,
        static_url_path="",
        static_folder="../../static",
        template_folder="../../templates",
    )
    app.register_blueprint(web)
    return app
