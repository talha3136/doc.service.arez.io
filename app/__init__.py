from flask import Flask
from flask_cors import CORS
from flask_restful import Api
from .config import Config
from .routes.api import api_bp
import logging

def create_app(config_name='default'):
    app = Flask(__name__)

    # Enable CORS
    # CORS(app, origins=["http://127.0.0.1:5500"])
    CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})


    # Load configuration
    config_class = Config.get(config_name)
    app.config.from_object(config_class)

    # Initialize logging
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)

    # Initialize API
    api = Api(app)

    # Register blueprints
    app.register_blueprint(api_bp)

    return app