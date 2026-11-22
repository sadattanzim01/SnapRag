# ─── Imports ──────────────────────────────────────────────────────────────────
import os
import re
from flask import Blueprint, request, jsonify
from anthropic import Anthropic
from services.embedder import find_relevant_chunks

chat_bp = Blueprint('chat', __name__)

MODEL = 'claude-sonnet-4-6'

# ─── Pattern for a generated document ────────────────────────────────────────
# Matches:  <document title="Study Guide"> ...markdown... </document>
# re.DOTALL lets "." match newlines, because documents span many lines.
DOC_PATTERN = re.compile(r'<document\s+title="([^"]*)">(.*?)</document>', re.DOTALL)

SYSTEM_PROMPT = (
    "You answer questions using ONLY the document excerpts provided. "
    "Cite sources like [Source 1] when you use them. "
    "If the excerpts do not contain the answer, say you could not find it "
    "in the uploaded documents. Do not use outside knowledge.\n\n"
    "If the user asks you to create, write, draft or compile a NEW document "
    "(a summary, report, study guide, comparison, outline, etc.), write it "
    "using only information from the excerpts. "
    "Do not add facts, descriptions or details that are not in the excerpts, "
    "even in generated documents. If something is missing, leave it out. "
    'Put the complete document in Markdown inside <document title="Short Title"> ... </document> tags, '
    "and keep your normal chat reply to one or two sentences OUTSIDE the tags. "
    "Never use the tags for ordinary answers."
)

# ─── POST /api/chat/ask ───────────────────────────────────────────────────────
@chat_bp.route('/ask', methods=['POST'])
def ask_question():
    """
    Expects JSON:
      {
        "question": "...",
        "document_ids": [1, 2],         # optional: limit search to these docs
        "history": [{"role": "user", "content": "..."}, ...]   # optional
      }
    Returns JSON:
      { "answer": "...", "sources": [...], "document": {title, content} | null }
    """
    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    if not question:
        return jsonify({'error': 'No question provided'}), 400

    # ── Which documents may be searched? ─────────────────────────────────────
    document_ids = None
    if data.get('document_ids') is not None:
        try:
            document_ids = [int(i) for i in data['document_ids']]
        except (TypeError, ValueError):
            return jsonify({'error': 'document_ids must be a list of numbers'}), 400

        # An empty list means the user unticked everything
        if not document_ids:
            return jsonify({
                'answer': 'Select at least one document in the sidebar first.',
                'sources': [],
                'document': None
            })

    # ── RETRIEVE ─────────────────────────────────────────────────────────────
    chunks = find_relevant_chunks(question, top_k=8, document_ids=document_ids)
    if not chunks:
        return jsonify({
            'answer': 'No documents have been uploaded yet. Upload a document first.',
            'sources': [],
            'document': None
        })

    # ── AUGMENT ──────────────────────────────────────────────────────────────
    context = "\n\n---\n\n".join(
        f"[Source {i}: {c['filename']}]\n{c['content']}"
        for i, c in enumerate(chunks, start=1)
    )
    user_message = f"Document excerpts:\n\n{context}\n\nQuestion: {question}"

    # ── Conversation memory ──────────────────────────────────────────────────
    # The API is stateless, so the frontend sends recent messages and we pass
    # them along. This makes follow-ups like "make it shorter" work.
    # Only the last 6 are kept, to limit cost.
    history = []
    for m in (data.get('history') or [])[-6:]:
        if m.get('role') in ('user', 'assistant') and isinstance(m.get('content'), str):
            history.append({'role': m['role'], 'content': m['content']})
    # The conversation must open with a user message
    while history and history[0]['role'] == 'assistant':
        history.pop(0)

    messages = history + [{'role': 'user', 'content': user_message}]

    # ── GENERATE ─────────────────────────────────────────────────────────────
    client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=3000,     # bigger, since a document is longer than an answer
            system=SYSTEM_PROMPT,
            messages=messages
        )
        raw = response.content[0].text
    except Exception as e:
        return jsonify({'error': f'Claude API error: {str(e)}'}), 500

    # ── Split the reply into chat text and an optional document ──────────────
    answer = raw
    document = None
    match = DOC_PATTERN.search(raw)
    if match:
        document = {
            'title': match.group(1).strip() or 'Generated document',
            'content': match.group(2).strip()
        }
        # Remove the document from the chat text, so it only shows on the right
        answer = DOC_PATTERN.sub('', raw).strip() or 'I created the document. It is open on the right.'

    sources = [
        {
            'filename': c['filename'],
            'similarity': round(c['similarity'], 3),
            'preview': c['content'][:150]
        }
        for c in chunks
    ]

    return jsonify({'answer': answer, 'sources': sources, 'document': document})