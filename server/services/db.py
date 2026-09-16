import os
import sqlite3
import json

# ─── Database path ────────────────────────────────────────────────────────────
# SQLite stores everything in a single file on disk — no server needed
# The file will be created automatically when the app first runs
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'snaprag.db')

def get_connection():
    """
    Creates a SQLite connection.
    SQLite is a file-based database — no server, no credentials, no network.
    Perfect for local development.
    """
    conn = sqlite3.connect(DB_PATH)
    # Makes rows return as dictionaries instead of plain tuples
    # So we get {'id': 1, 'filename': 'doc.pdf'} instead of (1, 'doc.pdf')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Creates the tables if they don't exist yet.
    Called once when the Flask server starts.
    SQLite automatically creates the .db file if it doesn't exist.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Documents table — stores metadata about each uploaded file
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            extracted_text TEXT,
            chunk_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Chunks table — stores each piece of text and its embedding
    # Embedding is stored as JSON text locally (real vector in production)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS document_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER REFERENCES documents(id),
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            embedding TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print('✅ Database initialized')

def execute_query(query, params=None, fetch=True):
    """
    Runs a SQL query and optionally returns results.
    fetch=True for SELECT queries — returns list of dicts
    fetch=False for INSERT/UPDATE/DELETE — commits and returns last row id
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or ())

        if fetch:
            rows = cursor.fetchall()
            # Convert sqlite3.Row objects to plain dicts
            return [dict(row) for row in rows]
        else:
            conn.commit()
            return cursor.lastrowid
    finally:
        # Always close the connection even if an error occurs
        conn.close()