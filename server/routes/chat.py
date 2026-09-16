from flask import Blueprint, jsonify

# Placeholder — we'll fill this in Phase 4
chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/test', methods=['GET'])
def test():
    return jsonify({'status': 'chat route working'})