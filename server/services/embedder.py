import json

from sentence_transformers import SentenceTransformer
from services.db import execute_query

# Loaded once at startup (small model, 384 numbers per text)
print('Loading embedding model...')
model = SentenceTransformer('all-MiniLM-L6-v2')
print('Embedding model loaded')


def chunk_text(text, chunk_size=200, overlap=50):
    """Split text into chunks of chunk_size words that share `overlap` words."""
    words = text.split()
    chunks = []

    i = 0
    while i < len(words):
        chunks.append(' '.join(words[i:i + chunk_size]))
        i += chunk_size - overlap

    return chunks


def embed_text(text):
    """Turn a string into a list of 384 floats."""
    return model.encode(text).tolist()


def cosine_similarity(vec1, vec2):
    """Similarity between two vectors, from 0 (different) to 1 (identical)."""
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a ** 2 for a in vec1) ** 0.5
    magnitude2 = sum(b ** 2 for b in vec2) ** 0.5

    if magnitude1 == 0 or magnitude2 == 0:
        return 0

    return dot_product / (magnitude1 * magnitude2)


def embed_and_store_document(document_id, text):
    """Chunk a document, embed every chunk, and save them. Returns the chunk count."""
    chunks = chunk_text(text)
    print(f'Split document into {len(chunks)} chunks')

    # One batch call is much faster than embedding chunks one by one
    embeddings = model.encode(chunks).tolist() if chunks else []

    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        execute_query(
            """
            INSERT INTO document_chunks (document_id, chunk_index, content, embedding)
            VALUES (?, ?, ?, ?)
            """,
            (document_id, i, chunk, json.dumps(embedding)),
            fetch=False
        )

    execute_query(
        'UPDATE documents SET chunk_count = ? WHERE id = ?',
        (len(chunks), document_id),
        fetch=False
    )

    print(f'Stored {len(chunks)} chunks')
    return len(chunks)


def find_relevant_chunks(question, top_k=8, document_ids=None):
    """
    Return the top_k chunks most similar to the question.
    If document_ids is given, only those documents are searched.
    """
    question_embedding = embed_text(question)

    query = """
        SELECT c.id, c.document_id, c.chunk_index, c.content, c.embedding,
               d.filename
        FROM document_chunks c
        JOIN documents d ON c.document_id = d.id
    """
    params = ()

    if document_ids:
        # One ? per id, so the ids are never pasted into the SQL text
        placeholders = ','.join('?' for _ in document_ids)
        query += f' WHERE c.document_id IN ({placeholders})'
        params = tuple(document_ids)

    chunks = execute_query(query, params)

    scored_chunks = []
    for chunk in chunks:
        chunk_embedding = json.loads(chunk['embedding'])
        scored_chunks.append({
            'content': chunk['content'],
            'document_id': chunk['document_id'],
            'filename': chunk['filename'],
            'chunk_index': chunk['chunk_index'],
            'similarity': cosine_similarity(question_embedding, chunk_embedding),
        })

    scored_chunks.sort(key=lambda x: x['similarity'], reverse=True)
    return scored_chunks[:top_k]