from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

from planner.models import Priority, Task

DEFAULT_DB = Path.home() / ".daily-planner" / "tasks.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    done        INTEGER NOT NULL DEFAULT 0,
    done_at     TEXT,
    priority    TEXT    NOT NULL DEFAULT 'medium',
    due_date    TEXT
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


_CREATE_TAGS_TABLE = """
CREATE TABLE IF NOT EXISTS task_tags (
    task_id INTEGER NOT NULL,
    tag     TEXT    NOT NULL,
    PRIMARY KEY (task_id, tag),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);
"""


def connect(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(_CREATE_TABLE)
    conn.execute(_CREATE_FOCUS_TABLE)
    conn.execute(_CREATE_TAGS_TABLE)
    _migrate(conn)
    conn.commit()
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    if "priority" not in columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN priority TEXT NOT NULL DEFAULT 'medium'")
    if "due_date" not in columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN due_date TEXT")


def add_task(
    conn: sqlite3.Connection,
    description: str,
    priority: Priority = Priority.MEDIUM,
    due_date: date | None = None,
    tags: list[str] | None = None,
) -> Task:
    today = date.today().isoformat()
    cur = conn.execute(
        "INSERT INTO tasks (description, created_at, priority, due_date) VALUES (?, ?, ?, ?)",
        (description, today, priority.value, due_date.isoformat() if due_date else None),
    )
    task_id = cur.lastrowid
    tag_list = tags or []
    for tag in tag_list:
        conn.execute(
            "INSERT INTO task_tags (task_id, tag) VALUES (?, ?)",
            (task_id, tag),
        )
    conn.commit()
    return Task(
        id=task_id,
        description=description,
        created_at=date.today(),
        priority=priority,
        due_date=due_date,
        tags=tag_list,
    )


def get_tasks_for_date(conn: sqlite3.Connection, day: date) -> list[Task]:
    rows = conn.execute(
        "SELECT id, description, created_at, done, done_at, priority, due_date FROM tasks WHERE created_at = ?",
        (day.isoformat(),),
    ).fetchall()
    tasks = [_row_to_task(r) for r in rows]
    _attach_tags(conn, tasks)
    return tasks


def get_tasks_between(conn: sqlite3.Connection, start: date, end: date) -> list[Task]:
    rows = conn.execute(
        "SELECT id, description, created_at, done, done_at, priority, due_date FROM tasks "
        "WHERE created_at BETWEEN ? AND ?",
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    tasks = [_row_to_task(r) for r in rows]
    _attach_tags(conn, tasks)
    return tasks


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
        "SELECT id, description, created_at, done, done_at, priority, due_date FROM tasks "
        "WHERE created_at < ? AND done = 0 "
        "ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 WHEN 'low' THEN 2 END",
        (before.isoformat(),),
    ).fetchall()
    tasks = [_row_to_task(r) for r in rows]
    _attach_tags(conn, tasks)
    return tasks


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
        f"SELECT id, description, created_at, done, done_at, priority, due_date FROM tasks WHERE id IN ({placeholders})",
        task_ids,
    ).fetchall()
    tasks = [_row_to_task(r) for r in rows]
    _attach_tags(conn, tasks)
    return tasks


def get_focus_ids(conn: sqlite3.Connection, day: date) -> set[int]:
    rows = conn.execute(
        "SELECT task_id FROM focus_tasks WHERE focus_date = ?",
        (day.isoformat(),),
    ).fetchall()
    return {r[0] for r in rows}


def get_past_deadline_tasks(conn: sqlite3.Connection, as_of: date) -> list[Task]:
    rows = conn.execute(
        "SELECT id, description, created_at, done, done_at, priority, due_date FROM tasks "
        "WHERE due_date < ? AND done = 0 "
        "ORDER BY due_date, CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 WHEN 'low' THEN 2 END",
        (as_of.isoformat(),),
    ).fetchall()
    tasks = [_row_to_task(r) for r in rows]
    _attach_tags(conn, tasks)
    return tasks


def get_tasks_due_on(conn: sqlite3.Connection, day: date) -> list[Task]:
    rows = conn.execute(
        "SELECT id, description, created_at, done, done_at, priority, due_date FROM tasks "
        "WHERE due_date = ? AND done = 0",
        (day.isoformat(),),
    ).fetchall()
    tasks = [_row_to_task(r) for r in rows]
    _attach_tags(conn, tasks)
    return tasks


def get_all_tasks(conn: sqlite3.Connection) -> list[Task]:
    rows = conn.execute(
        "SELECT id, description, created_at, done, done_at, priority, due_date FROM tasks",
    ).fetchall()
    tasks = [_row_to_task(r) for r in rows]
    _attach_tags(conn, tasks)
    return tasks


def get_daily_completion(conn: sqlite3.Connection) -> list[tuple[str, int, int]]:
    rows = conn.execute(
        "SELECT created_at, COUNT(*), SUM(done) FROM tasks GROUP BY created_at ORDER BY created_at",
    ).fetchall()
    return [(r[0], r[1], int(r[2])) for r in rows]


def get_tags_for_tasks(conn: sqlite3.Connection, task_ids: list[int]) -> dict[int, list[str]]:
    if not task_ids:
        return {}
    placeholders = ",".join("?" * len(task_ids))
    rows = conn.execute(
        f"SELECT task_id, tag FROM task_tags WHERE task_id IN ({placeholders}) ORDER BY tag",
        task_ids,
    ).fetchall()
    result: dict[int, list[str]] = {tid: [] for tid in task_ids}
    for task_id, tag in rows:
        result[task_id].append(tag)
    return result


def get_tasks_by_tag(conn: sqlite3.Connection, tag: str) -> list[Task]:
    rows = conn.execute(
        "SELECT t.id, t.description, t.created_at, t.done, t.done_at, t.priority, t.due_date "
        "FROM tasks t JOIN task_tags tt ON t.id = tt.task_id WHERE tt.tag = ?",
        (tag,),
    ).fetchall()
    tasks = [_row_to_task(r) for r in rows]
    _attach_tags(conn, tasks)
    return tasks


def get_all_tags(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    rows = conn.execute(
        "SELECT tag, COUNT(*) FROM task_tags GROUP BY tag ORDER BY COUNT(*) DESC, tag",
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def _attach_tags(conn: sqlite3.Connection, tasks: list[Task]) -> None:
    if not tasks:
        return
    tag_map = get_tags_for_tasks(conn, [t.id for t in tasks])
    for t in tasks:
        t.tags = tag_map.get(t.id, [])


def _row_to_task(row: tuple) -> Task:
    return Task(
        id=row[0],
        description=row[1],
        created_at=date.fromisoformat(row[2]),
        done=bool(row[3]),
        done_at=datetime.fromisoformat(row[4]) if row[4] else None,
        priority=Priority(row[5]),
        due_date=date.fromisoformat(row[6]) if row[6] else None,
    )
