from __future__ import annotations

import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).with_name("study_bot.db")


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database() -> None:
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                goal_id INTEGER NOT NULL,
                date TEXT NOT NULL DEFAULT CURRENT_DATE,
                duration_minutes INTEGER NOT NULL,
                total_tasks INTEGER NOT NULL,
                oral_tasks INTEGER NOT NULL,
                practical_tasks INTEGER NOT NULL,
                comment TEXT,
                FOREIGN KEY (goal_id) REFERENCES goals(id)
            )
        """)


def add_goal(user_id: int, name: str) -> None:
    with get_connection() as connection:
        connection.execute("INSERT INTO goals (user_id, name) VALUES (?, ?)", (user_id, name))


def get_goals(user_id: int) -> list[sqlite3.Row]:
    with get_connection() as connection:
        return connection.execute("SELECT id, name FROM goals WHERE user_id = ? ORDER BY id", (user_id,)).fetchall()


def get_goal(user_id: int, goal_id: int) -> sqlite3.Row | None:
    with get_connection() as connection:
        return connection.execute("SELECT id, name FROM goals WHERE id = ? AND user_id = ?", (goal_id, user_id)).fetchone()


def add_session(user_id: int, goal_id: int, data: dict) -> None:
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO sessions (user_id, goal_id, date, duration_minutes, total_tasks, oral_tasks, practical_tasks, comment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, goal_id, data.get("date"), data["duration_minutes"], data["total_tasks"], data["oral_tasks"], data["practical_tasks"], data.get("comment")))


def get_session(session_id: int, user_id: int, goal_id: int) -> sqlite3.Row | None:
    with get_connection() as connection:
        return connection.execute("""
            SELECT id, date, duration_minutes, total_tasks, oral_tasks, practical_tasks, comment
            FROM sessions WHERE id = ? AND user_id = ? AND goal_id = ?
        """, (session_id, user_id, goal_id)).fetchone()


def get_goal_stats(user_id: int, goal_id: int) -> sqlite3.Row:
    with get_connection() as connection:
        return connection.execute("""
            SELECT COALESCE(SUM(duration_minutes), 0) AS total_minutes, COUNT(id) AS session_count,
                   COALESCE(SUM(total_tasks), 0) AS total_tasks, COALESCE(SUM(oral_tasks), 0) AS oral_tasks,
                   COALESCE(SUM(practical_tasks), 0) AS practical_tasks, COALESCE(MAX(duration_minutes), 0) AS longest_session,
                   COALESCE((SELECT MAX(day_minutes) FROM (
                       SELECT SUM(duration_minutes) AS day_minutes FROM sessions
                       WHERE user_id = ? AND goal_id = ? GROUP BY date
                   )), 0) AS max_day_minutes
            FROM sessions WHERE user_id = ? AND goal_id = ?
        """, (user_id, goal_id, user_id, goal_id)).fetchone()


def get_sessions_by_date(user_id: int, goal_id: int, selected_date: str) -> list[sqlite3.Row]:
    with get_connection() as connection:
        return connection.execute("""
            SELECT id, date, duration_minutes, total_tasks, oral_tasks, practical_tasks, comment
            FROM sessions WHERE user_id = ? AND goal_id = ? AND date = ? ORDER BY id
        """, (user_id, goal_id, selected_date)).fetchall()


def update_session(session_id: int, user_id: int, data: dict) -> None:
    with get_connection() as connection:
        connection.execute("""
            UPDATE sessions SET date = ?, duration_minutes = ?, total_tasks = ?, oral_tasks = ?, practical_tasks = ?, comment = ?
            WHERE id = ? AND user_id = ?
        """, (data.get("date"), data["duration_minutes"], data["total_tasks"], data["oral_tasks"], data["practical_tasks"], data.get("comment"), session_id, user_id))


def reset_goal_sessions(user_id: int, goal_id: int) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM sessions WHERE user_id = ? AND goal_id = ?", (user_id, goal_id))
