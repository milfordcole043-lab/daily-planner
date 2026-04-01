from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

from planner.models import Task

DEFAULT_DB = Path.home() / ".daily-planner" / "tasks.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    done        INTEGER NOT NULL DEFAULT 0,
    done_at     TEXT
);
"""


def connect(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(_CREATE_TABLE)
    conn.commit()
    return conn


def add_task(conn: sqlite3.Connection, description: str) -> Task:
    today = date.today().isoformat()
    cur = conn.execute(
        "INSERT INTO tasks (description, created_at) VALUES (?, ?)",
        (description, today),
    )
    conn.commit()
    return Task(id=cur.lastrowid, description=description, created_at=date.today())


def get_tasks_for_date(conn: sqlite3.Connection, day: date) -> list[Task]:
    rows = conn.execute(
        "SELECT id, description, created_at, done, done_at FROM tasks WHERE created_at = ?",
        (day.isoformat(),),
    ).fetchall()
    return [_row_to_task(r) for r in rows]


def get_tasks_between(conn: sqlite3.Connection, start: date, end: date) -> list[Task]:
    rows = conn.execute(
        "SELECT id, description, created_at, done, done_at FROM tasks "
        "WHERE created_at BETWEEN ? AND ?",
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    return [_row_to_task(r) for r in rows]


def complete_task(conn: sqlite3.Connection, task_id: int) -> bool:
    now = datetime.now().isoformat()
    cur = conn.execute(
        "UPDATE tasks SET done = 1, done_at = ? WHERE id = ? AND done = 0",
        (now, task_id),
    )
    conn.commit()
    return cur.rowcount > 0


def remove_task(conn: sqlite3.Connection, task_id: int) -> bool:
    cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    return cur.rowcount > 0


def _row_to_task(row: tuple) -> Task:
    return Task(
        id=row[0],
        description=row[1],
        created_at=date.fromisoformat(row[2]),
        done=bool(row[3]),
        done_at=datetime.fromisoformat(row[4]) if row[4] else None,
    )
