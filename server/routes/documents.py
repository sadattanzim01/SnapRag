# ─── Imports ──────────────────────────────────────────────────────────────────
import os
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
from services.extractor import extract_text
from services.db import execute_query
from services.embedder import embed_and_store_document

# ─── Blueprint setup ──────────────────────────────────────────────────────────
# A Blueprint is Flask's way of grouping related routes
# 'documents' is the name, __name__ tells Flask where this file lives
# All routes here will be prefixed with /api/documents (set in app.py)
documents_bp = Blueprint('documents', __name__)

# ─── Allowed file types ───────────────────────────────────────────────────────
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

def allowed_file(filename):
    """
    Checks if an uploaded file has an allowed extension.
    
    'filename.rsplit('.', 1)' splits 'document.pdf' into ['document', 'pdf']
    We take index [1] to get just the extension, then lowercase it.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    """Returns 'pdf' or 'image' based on file extension."""
    ext = filename.rsplit('.', 1)[1].lower()
    return 'pdf' if ext == 'pdf' else 'image'

# ─── POST /api/documents/upload ───────────────────────────────────────────────
@documents_bp.route('/upload', methods=['POST'])
def upload_document():
    """
    Receives a file from the frontend, extracts its text,
    saves it to the uploads folder, and stores metadata in the database.
    
    Flow:
    1. Validate the file exists and has an allowed type
    2. Save it to the uploads/ folder
    3. Extract text using pdfplumber or pytesseract
    4. Save document metadata to the documents table
    5. Chunk and embed the document text
    6. Return the document ID so the frontend can track it
    """

    # ── Step 1: Check a file was actually sent ────────────────────────────────
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    # Empty filename means no file was selected
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Check the file extension is allowed
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    # ── Step 2: Save file to uploads/ folder ─────────────────────────────────
    filename = file.filename
    # secure_filename strips things like "../" so an uploaded filename can't
    # write outside the uploads folder
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(filename))
    file.save(file_path)

    file_type = get_file_type(filename)

    # ── Step 3: Extract text from the file ───────────────────────────────────
    try:
        extracted_text = extract_text(file_path, file_type)
    except Exception as e:
        return jsonify({'error': f'Text extraction failed: {str(e)}'}), 500

    if not extracted_text:
        return jsonify({'error': 'No text could be extracted from this file'}), 400

    # ── Step 4: Save document metadata to database ───────────────────────────
    # SQLite uses ? placeholders instead of %s (PostgreSQL syntax)
    # This prevents SQL injection attacks
    execute_query(
        """
        INSERT INTO documents (filename, file_type, extracted_text, chunk_count)
        VALUES (?, ?, ?, ?)
        """,
        (filename, file_type, extracted_text, 0),
        fetch=False
    )

    # SQLite doesn't support RETURNING — get the last inserted ID separately
    result = execute_query(
        "SELECT id FROM documents ORDER BY id DESC LIMIT 1",
        fetch=True
    )
    document_id = result[0]['id']

    # ── Step 5: Chunk and embed the document ─────────────────────────────────
    # This converts the text into vectors and stores them in the database
    # so we can do semantic search later
    chunk_count = embed_and_store_document(document_id, extracted_text)

    # ── Step 6: Return success with document info ─────────────────────────────
    return jsonify({
        'message': 'Document uploaded and text extracted successfully',
        'document_id': document_id,
        'filename': filename,
        'file_type': file_type,
        'chunk_count': chunk_count,
        'text_length': len(extracted_text),
        'preview': extracted_text[:200] + '...' if len(extracted_text) > 200 else extracted_text
    }), 201

# ─── GET /api/documents ───────────────────────────────────────────────────────
@documents_bp.route('/', methods=['GET'])
def get_documents():
    """
    Returns all uploaded documents from the database.
    The frontend uses this to show the document library.
    """
    documents = execute_query(
        "SELECT id, filename, file_type, chunk_count, created_at FROM documents ORDER BY created_at DESC"
    )
    return jsonify(documents)

# ─── DELETE /api/documents/<id> ───────────────────────────────────────────────
@documents_bp.route('/<int:document_id>', methods=['DELETE'])
def delete_document(document_id):
    """
    Deletes a document and all its chunks from the database.

    SQLite does not cascade deletes by default, so we delete the chunks
    ourselves first. Otherwise a deleted document's chunks would stay in
    document_chunks and could still show up in answers.
    """
    # Step 1: remove the document's chunks (and their embeddings)
    execute_query(
        "DELETE FROM document_chunks WHERE document_id = ?",
        (document_id,),
        fetch=False
    )

    # Step 2: remove the document row itself
    execute_query(
        "DELETE FROM documents WHERE id = ?",
        (document_id,),
        fetch=False
    )
    return jsonify({'message': 'Document deleted successfully'})


# ─── GET /api/documents/<id>/file ─────────────────────────────────────────────
@documents_bp.route('/<int:document_id>/file', methods=['GET'])
def get_document_file(document_id):
    """
    Sends the ORIGINAL uploaded file back to the browser, so the viewer
    panel can display the real PDF or image.
    """
    rows = execute_query(
        "SELECT filename FROM documents WHERE id = ?",
        (document_id,)
    )
    if not rows:
        return jsonify({'error': 'Document not found'}), 404

    # send_from_directory refuses paths outside the folder, and it sends the
    # file inline, so the browser displays it instead of downloading it.
    # A missing file on disk becomes a 404 automatically.
    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        secure_filename(rows[0]['filename'])
    )