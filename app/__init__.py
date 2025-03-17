# app/__init__.py
from flask import Flask
from pymongo import MongoClient
from config import Config  # Import the Config class

app = Flask(__name__)
app.config.from_object(Config)  # Load configuration from the Config class

# Initialize MongoDB
client = MongoClient(app.config['MONGO_URI'])
db = client[app.config['MONGO_DB_NAME']]

# Import routes
from app.routes.user_routes import user_bp
from app.routes.scan_routes import scan_bp

# Register blueprints
app.register_blueprint(user_bp)
app.register_blueprint(scan_bp)