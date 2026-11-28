import os

from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Load .env first so the other files can read the API key when they are imported
load_dotenv(override=True)

app = Flask(__name__)

# Let the React app (port 3000) call this server (port 5001)
CORS(app)

# Treat /api/documents and /api/documents/ as the same URL
app.url_map.strict_slashes = False

app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB upload limit
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# These imports come after load_dotenv on purpose
from services.db import init_db
from routes.documents import documents_bp
from routes.chat import chat_bp

init_db()

app.register_blueprint(documents_bp, url_prefix='/api/documents')
app.register_blueprint(chat_bp, url_prefix='/api/chat')


@app.route('/')
def health():
    return {'status': 'SnapRAG server is running'}


if __name__ == '__main__':
    app.run(debug=True, port=5001)