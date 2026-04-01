from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from planner import db


def test_add_task(conn: sqlite3.Connection) -> None:
    task = db.add_task(conn, "Write tests")
    assert task.id is not None
    assert task.description == "Write tests"
    assert task.created_at == date.today()
    assert task.done is False


def test_get_tasks_for_today(conn: sqlite3.Connection) -> None:
    db.add_task(conn, "Task A")
    db.add_task(conn, "Task B")
    tasks = db.get_tasks_for_date(conn, date.today())
    assert len(tasks) == 2


def test_complete_task(conn: sqlite3.Connection) -> None:
    task = db.add_task(conn, "Finish feature")
    assert db.complete_task(conn, task.id) is True
    tasks = db.get_tasks_for_date(conn, date.today())
    assert tasks[0].done is True
    assert tasks[0].done_at is not None


def test_complete_nonexistent_task(conn: sqlite3.Connection) -> None:
    assert db.complete_task(conn, 999) is False


def test_complete_already_done(conn: sqlite3.Connection) -> None:
    task = db.add_task(conn, "Already done")
    db.complete_task(conn, task.id)
    assert db.complete_task(conn, task.id) is False


def test_remove_task(conn: sqlite3.Connection) -> None:
    task = db.add_task(conn, "To remove")
    assert db.remove_task(conn, task.id) is True
    tasks = db.get_tasks_for_date(conn, date.today())
    assert len(tasks) == 0


def test_remove_nonexistent_task(conn: sqlite3.Connection) -> None:
    assert db.remove_task(conn, 999) is False


def test_get_tasks_between(conn: sqlite3.Connection) -> None:
    db.add_task(conn, "This week")
    tasks = db.get_tasks_between(conn, date.today(), date.today())
    assert len(tasks) == 1


def test_get_overdue_tasks(conn: sqlite3.Connection) -> None:
    # Insert a task with a past date directly
    conn.execute(
        "INSERT INTO tasks (description, created_at) VALUES (?, ?)",
        ("Old task", "2026-03-20"),
    )
    conn.commit()
    db.add_task(conn, "Today task")
    overdue = db.get_overdue_tasks(conn, date.today())
    assert len(overdue) == 1
    assert overdue[0].description == "Old task"


def test_get_overdue_excludes_done(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO tasks (description, created_at, done) VALUES (?, ?, 1)",
        ("Done old task", "2026-03-20"),
    )
    conn.commit()
    overdue = db.get_overdue_tasks(conn, date.today())
    assert len(overdue) == 0


def test_set_focus(conn: sqlite3.Connection) -> None:
    t1 = db.add_task(conn, "Task 1")
    t2 = db.add_task(conn, "Task 2")
    focused = db.set_focus(conn, [t1.id, t2.id], date.today())
    assert len(focused) == 2
    assert {t.id for t in focused} == {t1.id, t2.id}


def test_get_focus_ids(conn: sqlite3.Connection) -> None:
    t1 = db.add_task(conn, "Task 1")
    t2 = db.add_task(conn, "Task 2")
    db.set_focus(conn, [t1.id, t2.id], date.today())
    ids = db.get_focus_ids(conn, date.today())
    assert ids == {t1.id, t2.id}


def test_set_focus_max_three(conn: sqlite3.Connection) -> None:
    tasks = [db.add_task(conn, f"Task {i}") for i in range(4)]
    with pytest.raises(ValueError, match="at most 3"):
        db.set_focus(conn, [t.id for t in tasks], date.today())


def test_set_focus_replaces_previous(conn: sqlite3.Connection) -> None:
    t1 = db.add_task(conn, "Task 1")
    t2 = db.add_task(conn, "Task 2")
    db.set_focus(conn, [t1.id], date.today())
    db.set_focus(conn, [t2.id], date.today())
    ids = db.get_focus_ids(conn, date.today())
    assert ids == {t2.id}
