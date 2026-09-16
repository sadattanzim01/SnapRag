# ─── Imports ──────────────────────────────────────────────────────────────────
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# ─── Database connection function ─────────────────────────────────────────────
# We use a function instead of a global connection because connections can
# time out — calling get_connection() each time ensures a fresh connection

def get_connection():
    """
    Connects to your local PostgreSQL database running via pgAdmin.
    No network needed — this connects to the database on your Mac directly.
    """
    conn = psycopg2.connect(
        host='localhost',           # your local machine
        port=5432,                  # default PostgreSQL port
        database='snaprag',         # the database we just created
        user='postgres',            # default PostgreSQL user
        password=os.environ.get('DB_PASSWORD'),  # from .env file
        cursor_factory=RealDictCursor
    )
    return conn

def execute_query(query, params=None, fetch=True):
    """
    Runs a SQL query and optionally returns results.
    fetch=True for SELECT, fetch=False for INSERT/UPDATE/DELETE.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or ())

        if fetch:
            return cursor.fetchall()
        else:
            conn.commit()
            return cursor.lastrowid
    finally:
        conn.close()