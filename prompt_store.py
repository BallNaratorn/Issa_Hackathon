import os
import sqlite3
from datetime import datetime
from typing import Optional

DEFAULT_BASE_PROMPT = """
You are a friendly, human-sounding visa consultant working for Issa Compass.

Your job is to reply to potential customers who are asking about the Thai DTV (Destination Thailand Visa). You:
- Sound like a real human, not an AI
- Use casual, warm language similar to WhatsApp or LINE chats
- Are concise but supportive, and avoid long walls of text
- Use occasional emojis when they feel natural, but don't overdo it
- Are always honest about requirements and timelines
- Clearly explain next steps and gently move high-intent users towards downloading the app, uploading documents, or booking an appointment

You must ALWAYS respond in JSON format only, with this schema:
{ "reply": "string with your reply message" }

The input will contain:
- clientSequence: the latest 1+ messages from the client
- chatHistory: a list of earlier messages with roles "client" or "consultant"

Write your reply as if you are continuing the same chat thread. Do NOT repeat the client's question verbatim. Keep it natural and tailored to the specific situation.
""".strip()


def _get_db_path() -> str:
    return os.getenv("PROMPT_DB_PATH", "prompt_store.db")


def _ensure_db() -> None:
    path = _get_db_path()
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL,
                prompt_text TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _get_connection() -> sqlite3.Connection:
    _ensure_db()
    return sqlite3.connect(_get_db_path())


def get_latest_prompt() -> str:
    """
    Return the latest stored prompt text, or initialize with DEFAULT_BASE_PROMPT.
    """
    _ensure_db()
    conn = _get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT prompt_text FROM prompts ORDER BY version DESC LIMIT 1")
        row = cur.fetchone()
        if row and row[0]:
            return row[0]
    finally:
        conn.close()

    # If no prompt exists yet, seed the database.
    initialize_prompt_if_empty()
    conn = _get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT prompt_text FROM prompts ORDER BY version DESC LIMIT 1")
        row = cur.fetchone()
        return row[0] if row and row[0] else DEFAULT_BASE_PROMPT
    finally:
        conn.close()


def initialize_prompt_if_empty() -> None:
    """
    Seed the database with the DEFAULT_BASE_PROMPT if there are no prompts yet.
    """
    _ensure_db()
    conn = _get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM prompts")
        count = cur.fetchone()[0]
        if count == 0:
            now = datetime.utcnow().isoformat()
            cur.execute(
                "INSERT INTO prompts (version, prompt_text, created_at) VALUES (?, ?, ?)",
                (1, DEFAULT_BASE_PROMPT, now),
            )
            conn.commit()
    finally:
        conn.close()


def save_new_prompt(new_prompt: str) -> str:
    """
    Save a new version of the prompt and return it.
    """
    if not new_prompt or not new_prompt.strip():
        raise ValueError("new_prompt must be a non-empty string")

    _ensure_db()
    conn = _get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(version), 0) FROM prompts")
        current_version = cur.fetchone()[0] or 0
        next_version = current_version + 1

        now = datetime.utcnow().isoformat()
        cur.execute(
            "INSERT INTO prompts (version, prompt_text, created_at) VALUES (?, ?, ?)",
            (next_version, new_prompt.strip(), now),
        )
        conn.commit()
    finally:
        conn.close()

    return new_prompt.strip()


def list_prompt_versions(limit: int = 20) -> list[dict]:
    """
    Return a list of previous prompt versions (most recent first).
    """
    _ensure_db()
    conn = _get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT version, prompt_text, created_at
            FROM prompts
            ORDER BY version DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {"version": version, "prompt_text": prompt_text, "created_at": created_at}
        for (version, prompt_text, created_at) in rows
    ]

