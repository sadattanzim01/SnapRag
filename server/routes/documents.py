import os

from flask import Blueprint, request, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename

from services.extractor import extract_text
from services.db import execute_query
from services.embedder import embed_and_store_document

documents_bp = Blueprint('documents', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}


def get_extension(filename):
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''


def allowed_file(filename):
    return get_extension(filename) in ALLOWED_EXTENSIONS


def get_file_type(filename):
    return 'pdf' if get_extension(filename) == 'pdf' else 'image'


def stored_name(document_id, filename):
    """Name used on disk. The id keeps two uploads with the same filename apart."""
    base = secure_filename(os.path.splitext(filename)[0]) or 'file'
    return f'{document_id}_{base}.{get_extension(filename)}'


def discard_upload(document_id, file_path):
    """Remove a document row and its file after a failed upload."""
    execute_query('DELETE FROM documents WHERE id = ?', (document_id,), fetch=False)
    if os.path.exists(file_path):
        os.remove(file_path)


@documents_bp.route('/upload', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    filename = file.filename
    file_type = get_file_type(filename)

    # Insert first so the new id can be used in the saved file's name
    document_id = execute_query(
        'INSERT INTO documents (filename, file_type) VALUES (?, ?)',
        (filename, file_type),
        fetch=False
    )

    file_path = os.path.join(
        current_app.config['UPLOAD_FOLDER'], stored_name(document_id, filename)
    )
    file.save(file_path)

    try:
        extracted_text = extract_text(file_path, file_type)
    except Exception as e:
        discard_upload(document_id, file_path)
        return jsonify({'error': f'Text extraction failed: {str(e)}'}), 500

    if not extracted_text:
        discard_upload(document_id, file_path)
        return jsonify({'error': 'No text could be extracted from this file'}), 400

    execute_query(
        'UPDATE documents SET extracted_text = ? WHERE id = ?',
        (extracted_text, document_id),
        fetch=False
    )

    chunk_count = embed_and_store_document(document_id, extracted_text)

    preview = extracted_text[:200] + '...' if len(extracted_text) > 200 else extracted_text
    return jsonify({
        'message': 'Document uploaded and text extracted successfully',
        'document_id': document_id,
        'filename': filename,
        'file_type': file_type,
        'chunk_count': chunk_count,
        'text_length': len(extracted_text),
        'preview': preview
    }), 201


@documents_bp.route('/', methods=['GET'])
def get_documents():
    documents = execute_query(
        'SELECT id, filename, file_type, chunk_count, created_at '
        'FROM documents ORDER BY created_at DESC'
    )
    return jsonify(documents)


@documents_bp.route('/<int:document_id>', methods=['DELETE'])
def delete_document(document_id):
    rows = execute_query(
        'SELECT filename FROM documents WHERE id = ?', (document_id,)
    )
    if not rows:
        return jsonify({'error': 'Document not found'}), 404

    # SQLite doesn't cascade deletes, so remove the chunks first
    execute_query(
        'DELETE FROM document_chunks WHERE document_id = ?',
        (document_id,),
        fetch=False
    )
    execute_query('DELETE FROM documents WHERE id = ?', (document_id,), fetch=False)

    file_path = os.path.join(
        current_app.config['UPLOAD_FOLDER'], stored_name(document_id, rows[0]['filename'])
    )
    if os.path.exists(file_path):
        os.remove(file_path)

    return jsonify({'message': 'Document deleted successfully'})


@documents_bp.route('/<int:document_id>/file', methods=['GET'])
def get_document_file(document_id):
    """Send the original uploaded file so the viewer can show it."""
    rows = execute_query(
        'SELECT filename FROM documents WHERE id = ?', (document_id,)
    )
    if not rows:
        return jsonify({'error': 'Document not found'}), 404

    folder = current_app.config['UPLOAD_FOLDER']
    filename = rows[0]['filename']

    name = stored_name(document_id, filename)
    if not os.path.exists(os.path.join(folder, name)):
        # Files uploaded before unique names were added
        name = secure_filename(filename)

    return send_from_directory(folder, name)