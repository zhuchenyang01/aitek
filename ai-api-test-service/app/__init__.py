from flask import Flask

from app.config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    from app.api.health import health_bp
    from app.api.run import run_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(run_bp)
    return app
