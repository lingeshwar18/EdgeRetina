from flask import Flask

from .config import Config
from .database.database import initialize


def create_app(config_class=Config):
    app = Flask(__name__, template_folder="../../frontend/templates", static_folder="../../frontend/static")
    app.config.from_object(config_class)
    initialize(config_class.DATABASE_PATH)
    from .routes import register_routes

    register_routes(app)
    return app
