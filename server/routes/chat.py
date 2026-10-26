# ─── Imports ──────────────────────────────────────────────────────────────────
import os
from flask import Blueprint, request, jsonify
from anthropic import Anthropic
from services.embedder import find_relevant_chunks

# ─── Blueprint setup ──────────────────────────────────────────────────────────
# Routes here get the /api/chat prefix (set in app.py)
chat_bp = Blueprint('chat', __name__)

# ─── Claude model ─────────────────────────────────────────────────────────────
MODEL = 'claude-sonnet-4-6'

# ─── POST /api/chat/ask ───────────────────────────────────────────────────────
@chat_bp.route('/ask', methods=['POST'])
def ask_question():
    """
    Takes a question, retrieves relevant chunks, asks Claude, returns answer.

    Expects JSON:  { "question": "What is RAG?" }
    Returns JSON:  { "answer": "...", "sources": [...] }
    """

    # ── Step 1: Read and validate the question ───────────────────────────────
    # get_json(silent=True) returns None instead of crashing on bad JSON
    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()

    if not question:
        return jsonify({'error': 'No question provided'}), 400

    # ── Step 2: RETRIEVE — find the most relevant chunks ─────────────────────
    chunks = find_relevant_chunks(question, top_k=5)

    # If nothing is uploaded yet, there is nothing to answer from
    if not chunks:
        return jsonify({
            'answer': 'No documents have been uploaded yet. Upload a document first.',
            'sources': []
        })

    # ── Step 3: AUGMENT — build the context block for the prompt ─────────────
    # Each chunk is labelled with its source so Claude can cite it
    context_parts = []
    for i, chunk in enumerate(chunks, start=1):
        context_parts.append(
            f"[Source {i}: {chunk['filename']}]\n{chunk['content']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    # The system prompt sets Claude's rules.
    # Telling it to stay inside the context is what stops it from
    # making things up (hallucinating) about your documents.
    system_prompt = (
        "You answer questions using ONLY the document excerpts provided. "
        "Cite sources like [Source 1] when you use them. "
        "If the excerpts do not contain the answer, say you could not find "
        "it in the uploaded documents. Do not use outside knowledge."
    )

    user_message = f"Document excerpts:\n\n{context}\n\nQuestion: {question}"

    # ── Step 4: GENERATE — ask Claude ────────────────────────────────────────
    # Client is created inside the function so the API key from .env
    # is already loaded by the time it runs
    client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            system=system_prompt,
            messages=[{'role': 'user', 'content': user_message}]
        )
        answer = response.content[0].text
    except Exception as e:
        return jsonify({'error': f'Claude API error: {str(e)}'}), 500

    # ── Step 5: Return the answer plus the sources used ──────────────────────
    # The frontend will show these so users can verify the answer
    sources = [
        {
            'filename': c['filename'],
            'similarity': round(c['similarity'], 3),
            'preview': c['content'][:150]
        }
        for c in chunks
    ]

    return jsonify({'answer': answer, 'sources': sources})