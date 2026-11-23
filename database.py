"""
Модуль базы данных SQLite для проекта «Анкета» (tgbot).
Управляет пользователями, соответствием User ID <-> Topic ID в Telegram,
сохранением анкет и настройками.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tgbot.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Таблица пользователей и их топиков
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                user_name TEXT,
                thread_id INTEGER UNIQUE,
                survey_completed INTEGER DEFAULT 0,
                tags TEXT,
                care_answer TEXT,
                medical_note TEXT,
                allergy_note TEXT,
                answers_json TEXT,
                analysis_text TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Индекс для быстрого поиска пользователя по thread_id
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_thread_id ON users(thread_id)
        """)
        
        # Таблица системных настроек (например, operator_chat_id)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()
    logger.info("База данных tgbot.db инициализирована.")


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_thread_id(thread_id: int) -> Optional[Dict[str, Any]]:
    if not thread_id:
        return None
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE thread_id = ?", (thread_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def upsert_user_basic(user_id: int, username: Optional[str] = None, user_name: Optional[str] = None):
    now = datetime.now().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, username, user_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = COALESCE(excluded.username, users.username),
                user_name = COALESCE(excluded.user_name, users.user_name),
                updated_at = excluded.updated_at
        """, (user_id, username, user_name, now, now))
        conn.commit()


def save_survey_results(
    user_id: int,
    username: Optional[str],
    user_name: str,
    tags: List[str],
    care_answer: str,
    medical_note: Optional[str],
    allergy_note: Optional[str],
    answers_dict: Dict[str, Any],
    analysis_text: str
):
    now = datetime.now().isoformat()
    tags_json = json.dumps(tags, ensure_ascii=False)
    answers_json = json.dumps(answers_dict, ensure_ascii=False)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (
                user_id, username, user_name, survey_completed,
                tags, care_answer, medical_note, allergy_note,
                answers_json, analysis_text, created_at, updated_at
            )
            VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = COALESCE(excluded.username, users.username),
                user_name = excluded.user_name,
                survey_completed = 1,
                tags = excluded.tags,
                care_answer = excluded.care_answer,
                medical_note = excluded.medical_note,
                allergy_note = excluded.allergy_note,
                answers_json = excluded.answers_json,
                analysis_text = excluded.analysis_text,
                updated_at = excluded.updated_at
        """, (
            user_id, username, user_name,
            tags_json, care_answer, medical_note, allergy_note,
            answers_json, analysis_text, now, now
        ))
        conn.commit()


def set_user_thread_id(user_id: int, thread_id: int):
    now = datetime.now().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET thread_id = ?, updated_at = ? WHERE user_id = ?
        """, (thread_id, now, user_id))
        conn.commit()


def is_survey_completed(user_id: int) -> bool:
    user = get_user(user_id)
    return bool(user and user.get("survey_completed") == 1)


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, str(value)))
        conn.commit()
