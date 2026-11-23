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

        # Таблица активных диалогов (Оператор <-> Клиент, поддержка нескольких параллельных)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_dialogs (
                operator_id INTEGER,
                client_id INTEGER,
                is_focused INTEGER DEFAULT 1,
                started_at TEXT,
                PRIMARY KEY (operator_id, client_id)
            )
        """)

        # Таблица маршрутизации сообщений для ответа через Reply (свайп)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_routing (
                operator_msg_id INTEGER,
                operator_id INTEGER,
                client_id INTEGER,
                created_at TEXT,
                PRIMARY KEY (operator_msg_id, operator_id)
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_routing_client ON message_routing(client_id)
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


# ================== АКТИВНЫЕ ДИАЛОГИ И МАРШРУТИЗАЦИЯ ==================

def save_message_routing(operator_msg_id: int, operator_id: int, client_id: int):
    """Сохраняет соответствие сообщения у оператора и ID клиента (для ответа через Reply)."""
    now = datetime.now().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO message_routing (operator_msg_id, operator_id, client_id, created_at)
            VALUES (?, ?, ?, ?)
        """, (operator_msg_id, operator_id, client_id, now))
        conn.commit()


def get_client_by_operator_msg_id(operator_msg_id: int, operator_id: Optional[int] = None) -> Optional[int]:
    """Находит client_id по ID сообщения в чате оператора."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if operator_id:
            cursor.execute(
                "SELECT client_id FROM message_routing WHERE operator_msg_id = ? AND operator_id = ?",
                (operator_msg_id, operator_id)
            )
        else:
            cursor.execute(
                "SELECT client_id FROM message_routing WHERE operator_msg_id = ?",
                (operator_msg_id,)
            )
        row = cursor.fetchone()
        return row["client_id"] if row else None


def set_active_dialog(operator_id: int, client_id: int):
    """Активирует диалог с клиентом и переключает фокус оператора на него."""
    now = datetime.now().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        # Снимаем фокус с других диалогов этого оператора
        cursor.execute("UPDATE active_dialogs SET is_focused = 0 WHERE operator_id = ?", (operator_id,))
        # Добавляем или обновляем диалог с данным клиентом как сфокусированный
        cursor.execute("""
            INSERT INTO active_dialogs (operator_id, client_id, is_focused, started_at)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(operator_id, client_id) DO UPDATE SET is_focused = 1
        """, (operator_id, client_id, now))
        conn.commit()


def get_active_dialog_for_operator(operator_id: int) -> Optional[int]:
    """Возвращает client_id текущего сфокусированного диалога оператора (если оператор внутри чата)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT client_id FROM active_dialogs WHERE operator_id = ? AND is_focused = 1",
            (operator_id,)
        )
        row = cursor.fetchone()
        return row["client_id"] if row else None


def leave_current_chat(operator_id: int) -> Optional[int]:
    """Снимает фокус со всех диалогов оператора (выход из комнаты чата), сохраняя все диалоги открытыми."""
    focused = get_active_dialog_for_operator(operator_id)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE active_dialogs SET is_focused = 0 WHERE operator_id = ?", (operator_id,))
        conn.commit()
    return focused


def get_open_dialogs_for_operator(operator_id: int) -> List[Dict[str, Any]]:
    """Возвращает список всех открытых диалогов оператора."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.client_id, a.is_focused, a.started_at, u.user_name, u.username
            FROM active_dialogs a
            LEFT JOIN users u ON a.client_id = u.user_id
            WHERE a.operator_id = ?
            ORDER BY a.is_focused DESC, a.started_at DESC
        """, (operator_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_active_dialog_for_client(client_id: int) -> Optional[int]:
    """Возвращает operator_id, с которым открыт диалог у клиента."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT operator_id FROM active_dialogs WHERE client_id = ? ORDER BY is_focused DESC LIMIT 1",
            (client_id,)
        )
        row = cursor.fetchone()
        return row["operator_id"] if row else None


def switch_operator_focus(operator_id: int, client_id: int):
    """Переключает фокус оператора на указанного клиента."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE active_dialogs SET is_focused = 0 WHERE operator_id = ?", (operator_id,))
        cursor.execute(
            "UPDATE active_dialogs SET is_focused = 1 WHERE operator_id = ? AND client_id = ?",
            (operator_id, client_id)
        )
        conn.commit()


def close_active_dialog_for_operator(operator_id: int, client_id: Optional[int] = None) -> Optional[int]:
    """Закрывает диалог с указанным клиентом (или текущим сфокусированным) и возвращает client_id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if not client_id:
            client_id = get_active_dialog_for_operator(operator_id)

        if client_id:
            cursor.execute(
                "DELETE FROM active_dialogs WHERE operator_id = ? AND client_id = ?",
                (operator_id, client_id)
            )
            # Переключаем фокус на следующий оставшийся диалог, если он есть
            cursor.execute(
                "SELECT client_id FROM active_dialogs WHERE operator_id = ? ORDER BY started_at DESC LIMIT 1",
                (operator_id,)
            )
            next_row = cursor.fetchone()
            if next_row:
                cursor.execute(
                    "UPDATE active_dialogs SET is_focused = 1 WHERE operator_id = ? AND client_id = ?",
                    (operator_id, next_row["client_id"])
                )
            conn.commit()
            return client_id
    return None


def close_all_dialogs_for_operator(operator_id: int) -> List[int]:
    """Закрывает все открытые диалоги оператора и возвращает список client_id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT client_id FROM active_dialogs WHERE operator_id = ?", (operator_id,))
        clients = [row["client_id"] for row in cursor.fetchall()]
        cursor.execute("DELETE FROM active_dialogs WHERE operator_id = ?", (operator_id,))
        conn.commit()
        return clients


def close_active_dialog_for_client(client_id: int) -> Optional[int]:
    """Закрывает диалог со стороны клиента."""
    operator_id = get_active_dialog_for_client(client_id)
    if operator_id:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM active_dialogs WHERE client_id = ?", (client_id,))
            conn.commit()
    return operator_id
