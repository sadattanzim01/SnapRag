# ─── Standard library imports ───────────────────────────────────────────────
import os

# ─── Third-party imports ─────────────────────────────────────────────────────
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# ─── Load environment variables from .env file ───────────────────────────────
# This must happen FIRST before anything else so all os.environ values are set
load_dotenv()

# ─── Create the Flask app instance ───────────────────────────────────────────
app = Flask(__name__)

# ─── Enable CORS ─────────────────────────────────────────────────────────────
# Without this, the React frontend (port 3000) can't talk to Flask (port 5000)
# The browser blocks cross-origin requests by default for security
CORS(app)

# ─── Configure upload settings ───────────────────────────────────────────────
# MAX_CONTENT_LENGTH limits file upload size to 50MB
# UPLOAD_FOLDER is where we temporarily store uploaded files
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

# ─── Create uploads folder if it doesn't exist ───────────────────────────────
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ─── Initialize the database (creates tables if they don't exist) ─────────────
from services.db import init_db
init_db()

# ─── Import and register route blueprints ────────────────────────────────────
# Blueprints are Flask's way of organizing routes into separate files
# We import them here and register them with a URL prefix
from routes.documents import documents_bp
from routes.chat import chat_bp

app.register_blueprint(documents_bp, url_prefix='/api/documents')
app.register_blueprint(chat_bp, url_prefix='/api/chat')

# ─── Health check route ───────────────────────────────────────────────────────
# Simple endpoint to confirm the server is running
@app.route('/')
def health():
    return {'status': 'SnapRAG server is running 🚀'}

# ─── Start the server ────────────────────────────────────────────────────────
# debug=True enables auto-reload when files change (like nodemon)
# Only runs when this file is executed directly, not when imported
if __name__ == '__main__':
    app.run(debug=True, port=5001)
