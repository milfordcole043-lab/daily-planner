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

_CREATE_FOCUS_TABLE = """
CREATE TABLE IF NOT EXISTS focus_tasks (
    task_id    INTEGER NOT NULL,
    focus_date TEXT    NOT NULL,
    PRIMARY KEY (task_id, focus_date),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);
"""


def connect(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(_CREATE_TABLE)
    conn.execute(_CREATE_FOCUS_TABLE)
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


def get_overdue_tasks(conn: sqlite3.Connection, before: date) -> list[Task]:
    rows = conn.execute(
        "SELECT id, description, created_at, done, done_at FROM tasks "
        "WHERE created_at < ? AND done = 0",
        (before.isoformat(),),
    ).fetchall()
    return [_row_to_task(r) for r in rows]


def set_focus(conn: sqlite3.Connection, task_ids: list[int], day: date) -> list[Task]:
    if len(task_ids) > 3:
        raise ValueError("You can focus on at most 3 tasks per day.")
    conn.execute("DELETE FROM focus_tasks WHERE focus_date = ?", (day.isoformat(),))
    for tid in task_ids:
        conn.execute(
            "INSERT INTO focus_tasks (task_id, focus_date) VALUES (?, ?)",
            (tid, day.isoformat()),
        )
    conn.commit()
    if not task_ids:
        return []
    placeholders = ",".join("?" * len(task_ids))
    rows = conn.execute(
        f"SELECT id, description, created_at, done, done_at FROM tasks WHERE id IN ({placeholders})",
        task_ids,
    ).fetchall()
    return [_row_to_task(r) for r in rows]


def get_focus_ids(conn: sqlite3.Connection, day: date) -> set[int]:
    rows = conn.execute(
        "SELECT task_id FROM focus_tasks WHERE focus_date = ?",
        (day.isoformat(),),
    ).fetchall()
    return {r[0] for r in rows}


def _row_to_task(row: tuple) -> Task:
    return Task(
        id=row[0],
        description=row[1],
        created_at=date.fromisoformat(row[2]),
        done=bool(row[3]),
        done_at=datetime.fromisoformat(row[4]) if row[4] else None,
    )
