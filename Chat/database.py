import asyncio
import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

import psycopg
from psycopg.rows import dict_row

from env import POSTGRES_URI


async def get_conn(retries: int = 30, delay: float = 1.0):
    last_ex = None
    for _ in range(retries):
        try:
            return await psycopg.AsyncConnection.connect(POSTGRES_URI)
        except Exception as ex:
            last_ex = ex
            await asyncio.sleep(delay)
    raise last_ex


async def init_db():
    async with await get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                CREATE TABLE IF NOT EXISTS threads (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
            await cur.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
            await cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_thread_id
                ON messages(thread_id, created_at);
                """
            )
        await conn.commit()


async def create_thread(title: Optional[str] = None) -> Dict[str, Any]:
    thread_id = str(uuid.uuid4())
    if not title:
        title = "Global Chat"
    async with await get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "INSERT INTO threads (id, title) VALUES (%s, %s) RETURNING id, title, created_at, updated_at",
                (thread_id, title),
            )
            row = await cur.fetchone()
        await conn.commit()
    return _row_to_dict(row)


def _row_to_dict(row) -> Dict[str, Any]:
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


async def list_threads() -> List[Dict[str, Any]]:
    async with await get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT id, title, created_at, updated_at FROM threads ORDER BY updated_at DESC"
            )
            rows = await cur.fetchall()
    return [_row_to_dict(r) for r in rows]


async def get_thread(thread_id: str) -> Optional[Dict[str, Any]]:
    async with await get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT id, title, created_at, updated_at FROM threads WHERE id = %s",
                (thread_id,),
            )
            row = await cur.fetchone()
    return _row_to_dict(row) if row else None


async def add_message(thread_id: str, role: str, content: str) -> Dict[str, Any]:
    msg_id = str(uuid.uuid4())
    async with await get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE threads SET updated_at = NOW() WHERE id = %s",
                (thread_id,),
            )
            await cur.execute(
                "INSERT INTO messages (id, thread_id, role, content) VALUES (%s, %s, %s, %s) RETURNING id, thread_id, role, content, created_at",
                (msg_id, thread_id, role, content),
            )
            row = await cur.fetchone()
        await conn.commit()
    return {
        "id": row[0],
        "thread_id": row[1],
        "role": row[2],
        "content": row[3],
        "created_at": row[4].isoformat() if row[4] else None,
    }


async def get_messages(thread_id: str) -> List[Dict[str, Any]]:
    async with await get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT id, thread_id, role, content, created_at FROM messages WHERE thread_id = %s ORDER BY created_at ASC",
                (thread_id,),
            )
            rows = await cur.fetchall()
    return [_row_to_dict(r) for r in rows]


async def delete_thread(thread_id: str) -> bool:
    """Delete a thread. Messages are deleted automatically via ON DELETE CASCADE."""
    async with await get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM threads WHERE id = %s", (thread_id,))
            deleted = cur.rowcount
        await conn.commit()
    return deleted > 0


async def get_latest_assistant_message(thread_id: str) -> Optional[Dict[str, Any]]:
    async with await get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT id, thread_id, role, content, created_at FROM messages WHERE thread_id = %s AND role = 'assistant' ORDER BY created_at DESC LIMIT 1",
                (thread_id,),
            )
            row = await cur.fetchone()
    return _row_to_dict(row) if row else None