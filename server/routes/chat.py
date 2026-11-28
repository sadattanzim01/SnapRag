import os
import re

from flask import Blueprint, request, jsonify
from anthropic import Anthropic

from services.embedder import find_relevant_chunks

chat_bp = Blueprint('chat', __name__)

MODEL = 'claude-sonnet-4-6'

# Sources below this score are hidden from the list (Claude still sees them)
MIN_SOURCE_SIMILARITY = 0.1

# Matches <document title="..."> ... </document>; DOTALL so "." spans lines
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


def reply(answer):
    """A chat reply with no sources and no generated document."""
    return jsonify({'answer': answer, 'sources': [], 'document': None})


@chat_bp.route('/ask', methods=['POST'])
def ask_question():
    """
    Takes {question, document_ids (optional), history (optional)}.
    Returns {answer, sources, document}.
    """
    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    if not question:
        return jsonify({'error': 'No question provided'}), 400

    document_ids = None
    if data.get('document_ids') is not None:
        try:
            document_ids = [int(i) for i in data['document_ids']]
        except (TypeError, ValueError):
            return jsonify({'error': 'document_ids must be a list of numbers'}), 400

        # An empty list means every document is unticked
        if not document_ids:
            return reply('Select at least one document in the sidebar first.')

    chunks = find_relevant_chunks(question, top_k=8, document_ids=document_ids)
    if not chunks:
        if document_ids:
            return reply('The selected documents were not found. Refresh the page and try again.')
        return reply('No documents have been uploaded yet. Upload a document first.')

    context = '\n\n---\n\n'.join(
        f"[Source {i}: {c['filename']}]\n{c['content']}"
        for i, c in enumerate(chunks, start=1)
    )
    user_message = f'Document excerpts:\n\n{context}\n\nQuestion: {question}'

    # The API has no memory, so the last 6 messages are sent with each question
    history = []
    for m in (data.get('history') or [])[-6:]:
        if m.get('role') in ('user', 'assistant') and isinstance(m.get('content'), str):
            history.append({'role': m['role'], 'content': m['content']})
    # The conversation must start with a user message
    while history and history[0]['role'] == 'assistant':
        history.pop(0)

    messages = history + [{'role': 'user', 'content': user_message}]

    client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=3000,
            system=SYSTEM_PROMPT,
            messages=messages
        )
        raw = response.content[0].text
    except Exception as e:
        return jsonify({'error': f'Claude API error: {str(e)}'}), 500

    # Split the reply into chat text and an optional generated document
    answer = raw
    document = None
    match = DOC_PATTERN.search(raw)
    if match:
        document = {
            'title': match.group(1).strip() or 'Generated document',
            'content': match.group(2).strip()
        }
        answer = DOC_PATTERN.sub('', raw).strip() or 'I created the document. It is open on the right.'

    # Chunks are sorted best-first, so keeping the top one is the fallback
    shown = [c for c in chunks if c['similarity'] >= MIN_SOURCE_SIMILARITY] or chunks[:1]
    sources = [
        {
            'filename': c['filename'],
            'similarity': round(c['similarity'], 3),
            'preview': c['content'][:150]
        }
        for c in shown
    ]

    return jsonify({'answer': answer, 'sources': sources, 'document': document})