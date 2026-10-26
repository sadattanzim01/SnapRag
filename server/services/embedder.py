# ─── Imports ──────────────────────────────────────────────────────────────────
import json
from sentence_transformers import SentenceTransformer
from services.db import execute_query

# ─── Load the embedding model ─────────────────────────────────────────────────
# all-MiniLM-L6-v2 is a small, fast model that converts text into 384 numbers
# It downloads automatically the first time (~90MB) and caches locally
# We load it ONCE at module level so it's not reloaded on every request
print("⏳ Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("✅ Embedding model loaded")

# ─── Chunking ─────────────────────────────────────────────────────────────────
def chunk_text(text, chunk_size=200, overlap=50):
    """
    Splits a long text into smaller overlapping chunks.

    Why chunk?
    - Embedding a 10,000 word document as one vector loses too much detail
    - Smaller chunks = more precise search results
    - Overlap ensures we don't cut sentences awkwardly at chunk boundaries

    Example with chunk_size=5, overlap=2:
    Text: [1,2,3,4,5,6,7,8,9,10]
    Chunks: [1,2,3,4,5], [4,5,6,7,8], [7,8,9,10]
    The overlap (2 words) appears in both adjacent chunks.

    Args:
        text: the full extracted text string
        chunk_size: number of words per chunk (default 200)
        overlap: number of words shared between adjacent chunks (default 50)
    Returns:
        list of text chunk strings
    """
    # Split text into individual words
    words = text.split()
    chunks = []

    # Step through the words with a sliding window
    # Each step moves forward by (chunk_size - overlap) words
    i = 0
    while i < len(words):
        # Take chunk_size words starting at position i
        chunk_words = words[i:i + chunk_size]
        chunk = ' '.join(chunk_words)
        chunks.append(chunk)

        # Move forward by chunk_size minus overlap
        # This creates the overlap between adjacent chunks
        i += chunk_size - overlap

        # Stop if we've covered all words
        if i >= len(words):
            break

    return chunks

# ─── Embedding ────────────────────────────────────────────────────────────────
def embed_text(text):
    """
    Converts a text string into a vector of 384 numbers.

    How it works:
    - The sentence-transformers model reads the text
    - It outputs a list of 384 floating point numbers
    - Similar texts produce similar vectors (close in 384-dimensional space)
    - This is what makes semantic search possible

    Example:
    "The cat sat on the mat" → [0.12, -0.45, 0.78, ...]  (384 numbers)
    "A cat rested on a rug"  → [0.11, -0.43, 0.76, ...]  (very similar!)
    "The stock market fell"  → [-0.89, 0.23, -0.54, ...] (very different)

    Args:
        text: string to embed
    Returns:
        list of 384 floats
    """
    # encode() returns a numpy array — we convert to a plain Python list
    embedding = model.encode(text)
    return embedding.tolist()

# ─── Cosine Similarity ────────────────────────────────────────────────────────
def cosine_similarity(vec1, vec2):
    """
    Measures how similar two vectors are (0 = different, 1 = identical).

    This is how we find relevant chunks for a question:
    - Embed the question → get vector A
    - Embed each chunk → get vector B
    - Calculate cosine similarity between A and B
    - Return the chunks with highest similarity scores

    We calculate this manually since SQLite can't do vector math.
    In production (PostgreSQL + pgvector), the database does this natively.

    Args:
        vec1, vec2: lists of 384 floats
    Returns:
        float between 0 and 1
    """
    # Dot product: multiply corresponding elements and sum
    dot_product = sum(a * b for a, b in zip(vec1, vec2))

    # Magnitude: square root of sum of squares
    magnitude1 = sum(a ** 2 for a in vec1) ** 0.5
    magnitude2 = sum(b ** 2 for b in vec2) ** 0.5

    # Avoid division by zero
    if magnitude1 == 0 or magnitude2 == 0:
        return 0

    return dot_product / (magnitude1 * magnitude2)

# ─── Store chunks + embeddings in database ────────────────────────────────────
def embed_and_store_document(document_id, text):
    """
    Takes a document's full text, splits it into chunks,
    embeds each chunk, and stores everything in the database.

    This is called after a document is uploaded and text is extracted.

    Args:
        document_id: the ID of the document in the documents table
        text: the full extracted text of the document
    Returns:
        number of chunks created
    """
    # Step 1: Split text into chunks
    chunks = chunk_text(text)
    print(f"📄 Split document into {len(chunks)} chunks")

    # Step 2: Embed each chunk and store it
    for i, chunk in enumerate(chunks):
        # Convert chunk to vector
        embedding = embed_text(chunk)

        # Store chunk + embedding in database
        # Embedding stored as JSON string (SQLite doesn't support vector type)
        execute_query(
            """
            INSERT INTO document_chunks (document_id, chunk_index, content, embedding)
            VALUES (?, ?, ?, ?)
            """,
            (document_id, i, chunk, json.dumps(embedding)),
            fetch=False
        )

    # Step 3: Update the document's chunk_count
    execute_query(
        "UPDATE documents SET chunk_count = ? WHERE id = ?",
        (len(chunks), document_id),
        fetch=False
    )

    print(f"✅ Stored {len(chunks)} chunks with embeddings")
    return len(chunks)

# ─── Find relevant chunks for a question ──────────────────────────────────────
def find_relevant_chunks(question, top_k=5):
    """
    Finds the chunks most semantically similar to the question.

    Changes from before:
    - JOINs the documents table so each chunk comes back with its filename
      (needed so Claude and the user can see WHERE an answer came from)
    """
    # Step 1: Embed the question into 384 numbers
    question_embedding = embed_text(question)

    # Step 2: Load all chunks along with their document's filename
    # JOIN = combine rows from two tables where document_id matches id
    chunks = execute_query(
        """
        SELECT c.id, c.document_id, c.chunk_index, c.content, c.embedding,
               d.filename
        FROM document_chunks c
        JOIN documents d ON c.document_id = d.id
        """
    )

    if not chunks:
        return []

    # Step 3: Score every chunk against the question
    scored_chunks = []
    for chunk in chunks:
        # Embeddings are stored as JSON text, so turn it back into a list
        chunk_embedding = json.loads(chunk['embedding'])
        similarity = cosine_similarity(question_embedding, chunk_embedding)

        scored_chunks.append({
            'content': chunk['content'],
            'document_id': chunk['document_id'],
            'filename': chunk['filename'],
            'chunk_index': chunk['chunk_index'],
            'similarity': similarity
        })

    # Step 4: Highest similarity first, keep only the top_k
    scored_chunks.sort(key=lambda x: x['similarity'], reverse=True)
    return scored_chunks[:top_k]