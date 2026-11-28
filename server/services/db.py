import os
import sqlite3

# The database is one file next to the server folder
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'snaprag.db'))


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    # Rows can be read by column name, like row['filename']
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the tables if they don't exist yet."""
    conn = get_connection()
    cursor = conn.cursor()

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

    # The embedding is stored as JSON text
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

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_chunks_document
        ON document_chunks(document_id)
    ''')

    conn.commit()
    conn.close()
    print('Database initialized')


def execute_query(query, params=None, fetch=True):
    """
    fetch=True: run a SELECT and return a list of dicts.
    fetch=False: run an INSERT/UPDATE/DELETE, commit, and return the last row id.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or ())

        if fetch:
            return [dict(row) for row in cursor.fetchall()]

        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()