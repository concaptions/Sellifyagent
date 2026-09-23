import json
import logging
from datetime import datetime, timezone
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

from src.config import DATABASE_URL

logger = logging.getLogger(__name__)


@contextmanager
def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# Sellify runs against Cue's Supabase database, where n8n Cue is still live and
# owns the pa_* tables (pa_users, pa_reminders, pa_personas, pa_knowledge_chunks).
# While both systems run in parallel, Sellify writes only to its own sellify_*
# tables: writing to pa_users would double-count every message on the live
# user's row (both bots handle each one). Cue's tables are read-only to Sellify
# until n8n Cue is switched off and Sellify takes them over.
def _lock_tables(cur, *tables: str) -> None:
    """Enable row-level security with no policies.

    Supabase serves every table in the public schema over its REST API, and
    the anon key that API accepts is designed to be public. A table without
    RLS is therefore readable by anyone holding that key — for these tables,
    users' notes and uploaded documents (which can be health records). RLS
    with no policies denies the REST API entirely, matching Cue's pa_* tables;
    this app connects as the table owner, which bypasses RLS, so it's unaffected.
    """
    for table in tables:
        cur.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def init_database():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sellify_users (
                id SERIAL PRIMARY KEY,
                phone TEXT UNIQUE NOT NULL,
                name TEXT,
                timezone TEXT DEFAULT 'Asia/Singapore',
                profile JSONB DEFAULT '{}',
                message_count INT DEFAULT 0,
                last_msg_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS sellify_notes (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT[] DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS sellify_chat_history (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_calls JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_sellify_users_phone ON sellify_users(phone);
            CREATE INDEX IF NOT EXISTS idx_sellify_notes_user ON sellify_notes(user_id);
            CREATE INDEX IF NOT EXISTS idx_sellify_chat_history_user ON sellify_chat_history(user_id);
        """)
        _lock_tables(cur, "sellify_users", "sellify_notes", "sellify_chat_history")
        conn.commit()
        logger.info("Database tables initialized")

    # Separate transaction: if pgvector isn't available, only document search
    # degrades — notes and chat history above are already committed.
    try:
        init_document_tables()
    except Exception as e:
        logger.warning("Document tables not initialized: %s", e)


def init_document_tables():
    """Per-user uploaded documents (PDF/DOCX/text) and their searchable chunks.

    Only extracted text is kept, not the original file: less sensitive data
    held at rest, and deletion is a single cascade. embedding is nullable so a
    document is still stored and keyword-searchable without an OpenAI key.
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE EXTENSION IF NOT EXISTS vector;

            CREATE TABLE IF NOT EXISTS sellify_documents (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                content_type TEXT,
                size_bytes INT,
                char_count INT,
                content_hash TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                supersedes_id INT REFERENCES sellify_documents(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (user_id, content_hash)
            );

            CREATE TABLE IF NOT EXISTS sellify_document_chunks (
                id SERIAL PRIMARY KEY,
                document_id INT NOT NULL REFERENCES sellify_documents(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL,
                chunk_index INT NOT NULL,
                content TEXT NOT NULL,
                embedding vector(1536)
            );

            CREATE INDEX IF NOT EXISTS idx_sellify_documents_user ON sellify_documents(user_id);
            CREATE INDEX IF NOT EXISTS idx_sellify_document_chunks_user ON sellify_document_chunks(user_id);
        """)
        _lock_tables(cur, "sellify_documents", "sellify_document_chunks")
        logger.info("Document tables initialized")


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.7f}" for v in values) + "]"


def find_document_by_hash(user_id: str, content_hash: str) -> dict | None:
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, filename, created_at FROM sellify_documents WHERE user_id = %s AND content_hash = %s",
            (user_id, content_hash),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def save_document(
    user_id: str,
    filename: str,
    content_type: str,
    size_bytes: int,
    content_hash: str,
    chunks: list[str],
    embeddings: list[list[float]] | None,
) -> dict:
    """Store a document and its chunks in one transaction.

    A re-upload under the same filename supersedes the previous active copy
    (kept, but excluded from search) rather than deleting it: the user may
    still want the old version, and deletion should be their explicit choice.
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT id FROM sellify_documents
               WHERE user_id = %s AND filename = %s AND status = 'active'
               ORDER BY created_at DESC LIMIT 1""",
            (user_id, filename),
        )
        prev = cur.fetchone()
        supersedes_id = prev[0] if prev else None
        if supersedes_id:
            cur.execute(
                "UPDATE sellify_documents SET status = 'superseded' WHERE id = %s AND user_id = %s",
                (supersedes_id, user_id),
            )

        cur.execute(
            """INSERT INTO sellify_documents
               (user_id, filename, content_type, size_bytes, char_count, content_hash, supersedes_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (user_id, filename, content_type, size_bytes, sum(len(c) for c in chunks), content_hash, supersedes_id),
        )
        doc_id = cur.fetchone()[0]

        for i, chunk in enumerate(chunks):
            emb = _vector_literal(embeddings[i]) if embeddings else None
            cur.execute(
                """INSERT INTO sellify_document_chunks (document_id, user_id, chunk_index, content, embedding)
                   VALUES (%s, %s, %s, %s, %s::vector)""",
                (doc_id, user_id, i, chunk, emb),
            )
        return {"id": doc_id, "supersedes_id": supersedes_id}


def list_documents(user_id: str) -> list[dict]:
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """SELECT id, filename, content_type, char_count, status, supersedes_id, created_at
               FROM sellify_documents WHERE user_id = %s ORDER BY created_at DESC""",
            (user_id,),
        )
        return [dict(r) for r in cur.fetchall()]


def search_document_chunks(
    user_id: str, query: str, query_embedding: list[float] | None, limit: int = 5
) -> list[dict]:
    """Semantic search when an embedding is available, keyword search otherwise.
    Superseded documents are excluded; always scoped to user_id."""
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if query_embedding:
            cur.execute(
                """SELECT c.content, c.chunk_index, d.id AS document_id, d.filename,
                          1 - (c.embedding <=> %s::vector) AS score
                   FROM sellify_document_chunks c
                   JOIN sellify_documents d ON d.id = c.document_id
                   WHERE c.user_id = %s AND d.user_id = %s AND d.status = 'active'
                     AND c.embedding IS NOT NULL
                   ORDER BY c.embedding <=> %s::vector LIMIT %s""",
                (_vector_literal(query_embedding), user_id, user_id, _vector_literal(query_embedding), limit),
            )
            rows = [dict(r) for r in cur.fetchall()]
            if rows:
                return rows
        cur.execute(
            """SELECT c.content, c.chunk_index, d.id AS document_id, d.filename, NULL AS score
               FROM sellify_document_chunks c
               JOIN sellify_documents d ON d.id = c.document_id
               WHERE c.user_id = %s AND d.user_id = %s AND d.status = 'active'
                 AND c.content ILIKE %s
               ORDER BY d.created_at DESC, c.chunk_index LIMIT %s""",
            (user_id, user_id, f"%{query}%", limit),
        )
        return [dict(r) for r in cur.fetchall()]


def delete_document(user_id: str, document_id: int) -> str | None:
    """Hard delete (chunks cascade). Returns the filename, or None if the
    document doesn't exist for this user — never touches another user's rows."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM sellify_documents WHERE id = %s AND user_id = %s RETURNING filename",
            (document_id, user_id),
        )
        row = cur.fetchone()
        return row[0] if row else None


def upsert_user(phone: str, name: str | None = None) -> dict:
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            INSERT INTO sellify_users (phone, name, message_count, last_msg_at)
            VALUES (%s, %s, 1, NOW())
            ON CONFLICT (phone) DO UPDATE SET
                message_count = sellify_users.message_count + 1,
                last_msg_at = NOW(),
                updated_at = NOW()
            RETURNING *
        """, (phone, name))
        return dict(cur.fetchone())


def get_user(phone: str) -> dict | None:
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM sellify_users WHERE phone = %s", (phone,))
        row = cur.fetchone()
        return dict(row) if row else None


def save_note(user_id: str, title: str, content: str, tags: list[str] | None = None) -> int:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sellify_notes (user_id, title, content, tags)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (user_id, title, content, tags or []))
        return cur.fetchone()[0]


def get_notes(user_id: str, limit: int = 20) -> list[dict]:
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT id, title, content, tags, created_at, updated_at
            FROM sellify_notes WHERE user_id = %s
            ORDER BY updated_at DESC LIMIT %s
        """, (user_id, limit))
        return [dict(r) for r in cur.fetchall()]


def search_notes(user_id: str, query: str) -> list[dict]:
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT id, title, content, tags, created_at
            FROM sellify_notes
            WHERE user_id = %s
              AND (title ILIKE %s OR content ILIKE %s)
            ORDER BY updated_at DESC LIMIT 10
        """, (user_id, f"%{query}%", f"%{query}%"))
        return [dict(r) for r in cur.fetchall()]


def save_chat_message(user_id: str, role: str, content: str, tool_calls: dict | None = None):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sellify_chat_history (user_id, role, content, tool_calls)
            VALUES (%s, %s, %s, %s)
        """, (user_id, role, content, json.dumps(tool_calls) if tool_calls else None))


def get_chat_history(user_id: str, limit: int = 50) -> list[dict]:
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT role, content, tool_calls, created_at
            FROM sellify_chat_history
            WHERE user_id = %s
            ORDER BY created_at DESC LIMIT %s
        """, (user_id, limit))
        rows = [dict(r) for r in cur.fetchall()]
        rows.reverse()
        return rows
