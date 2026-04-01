from __future__ import annotations

import sqlite3
from datetime import date

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
