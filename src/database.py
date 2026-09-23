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
        conn.commit()
        logger.info("Database tables initialized")


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
