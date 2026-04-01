from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from planner import db
from planner.models import Priority


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


# --- Priority & deadline tests ---


def test_add_task_default_priority(conn: sqlite3.Connection) -> None:
    task = db.add_task(conn, "Default priority")
    assert task.priority == Priority.MEDIUM
    assert task.due_date is None


def test_add_task_with_priority(conn: sqlite3.Connection) -> None:
    task = db.add_task(conn, "Urgent", priority=Priority.HIGH)
    assert task.priority == Priority.HIGH
    tasks = db.get_tasks_for_date(conn, date.today())
    assert tasks[-1].priority == Priority.HIGH


def test_add_task_with_due_date(conn: sqlite3.Connection) -> None:
    due = date(2026, 4, 5)
    task = db.add_task(conn, "Has deadline", due_date=due)
    assert task.due_date == due
    tasks = db.get_tasks_for_date(conn, date.today())
    assert tasks[-1].due_date == due


def test_get_past_deadline_tasks(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO tasks (description, created_at, due_date) VALUES (?, ?, ?)",
        ("Overdue task", date.today().isoformat(), "2026-03-25"),
    )
    conn.commit()
    tasks = db.get_past_deadline_tasks(conn, date(2026, 3, 30))
    assert len(tasks) == 1
    assert tasks[0].description == "Overdue task"


def test_get_past_deadline_excludes_done(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO tasks (description, created_at, due_date, done) VALUES (?, ?, ?, 1)",
        ("Done task", date.today().isoformat(), "2026-03-25"),
    )
    conn.commit()
    tasks = db.get_past_deadline_tasks(conn, date(2026, 3, 30))
    assert len(tasks) == 0


def test_get_past_deadline_excludes_future(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO tasks (description, created_at, due_date) VALUES (?, ?, ?)",
        ("Future task", date.today().isoformat(), "2026-04-10"),
    )
    conn.commit()
    tasks = db.get_past_deadline_tasks(conn, date(2026, 4, 1))
    assert len(tasks) == 0


def test_get_tasks_due_on(conn: sqlite3.Connection) -> None:
    target = date(2026, 4, 1)
    conn.execute(
        "INSERT INTO tasks (description, created_at, due_date) VALUES (?, ?, ?)",
        ("Due today", date.today().isoformat(), target.isoformat()),
    )
    conn.execute(
        "INSERT INTO tasks (description, created_at, due_date) VALUES (?, ?, ?)",
        ("Due tomorrow", date.today().isoformat(), "2026-04-02"),
    )
    conn.commit()
    tasks = db.get_tasks_due_on(conn, target)
    assert len(tasks) == 1
    assert tasks[0].description == "Due today"


# --- Tag tests ---


def test_add_task_with_tags(conn: sqlite3.Connection) -> None:
    task = db.add_task(conn, "Tagged task", tags=["code", "urgent"])
    assert sorted(task.tags) == ["code", "urgent"]
    tasks = db.get_tasks_for_date(conn, date.today())
    assert sorted(tasks[0].tags) == ["code", "urgent"]


def test_get_tags_for_tasks(conn: sqlite3.Connection) -> None:
    t1 = db.add_task(conn, "Task 1", tags=["code"])
    t2 = db.add_task(conn, "Task 2", tags=["personal", "health"])
    tag_map = db.get_tags_for_tasks(conn, [t1.id, t2.id])
    assert tag_map[t1.id] == ["code"]
    assert sorted(tag_map[t2.id]) == ["health", "personal"]


def test_get_tasks_by_tag(conn: sqlite3.Connection) -> None:
    db.add_task(conn, "Code task", tags=["code"])
    db.add_task(conn, "Personal task", tags=["personal"])
    db.add_task(conn, "Both", tags=["code", "personal"])
    tasks = db.get_tasks_by_tag(conn, "code")
    assert len(tasks) == 2
    descriptions = {t.description for t in tasks}
    assert descriptions == {"Code task", "Both"}


def test_get_all_tags(conn: sqlite3.Connection) -> None:
    db.add_task(conn, "Task 1", tags=["code", "urgent"])
    db.add_task(conn, "Task 2", tags=["code"])
    tag_counts = db.get_all_tags(conn)
    tag_dict = dict(tag_counts)
    assert tag_dict["code"] == 2
    assert tag_dict["urgent"] == 1


def test_get_all_tags_empty(conn: sqlite3.Connection) -> None:
    tag_counts = db.get_all_tags(conn)
    assert tag_counts == []


def test_overdue_tasks_sorted_by_priority(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO tasks (description, created_at, priority) VALUES (?, ?, ?)",
        ("Low task", "2026-03-20", "low"),
    )
    conn.execute(
        "INSERT INTO tasks (description, created_at, priority) VALUES (?, ?, ?)",
        ("High task", "2026-03-20", "high"),
    )
    conn.execute(
        "INSERT INTO tasks (description, created_at, priority) VALUES (?, ?, ?)",
        ("Medium task", "2026-03-20", "medium"),
    )
    conn.commit()
    tasks = db.get_overdue_tasks(conn, date.today())
    assert tasks[0].description == "High task"
    assert tasks[1].description == "Medium task"
    assert tasks[2].description == "Low task"


# --- Stats & streak tests ---


def test_get_all_tasks(conn: sqlite3.Connection) -> None:
    db.add_task(conn, "Task 1")
    db.add_task(conn, "Task 2")
    db.complete_task(conn, 1)
    tasks = db.get_all_tasks(conn)
    assert len(tasks) == 2
    assert sum(1 for t in tasks if t.done) == 1


def test_get_all_tasks_empty(conn: sqlite3.Connection) -> None:
    assert db.get_all_tasks(conn) == []


def test_get_daily_completion(conn: sqlite3.Connection) -> None:
    # Insert tasks on two different days
    conn.execute(
        "INSERT INTO tasks (description, created_at, done) VALUES (?, ?, 1)",
        ("Done task", "2026-03-25"),
    )
    conn.execute(
        "INSERT INTO tasks (description, created_at, done) VALUES (?, ?, 0)",
        ("Pending task", "2026-03-25"),
    )
    conn.execute(
        "INSERT INTO tasks (description, created_at, done) VALUES (?, ?, 1)",
        ("All done", "2026-03-26"),
    )
    conn.commit()
    rows = db.get_daily_completion(conn)
    assert len(rows) == 2
    # First day: 2 total, 1 completed
    assert rows[0] == ("2026-03-25", 2, 1)
    # Second day: 1 total, 1 completed
    assert rows[1] == ("2026-03-26", 1, 1)
