from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from planner.cli import cli


def _invoke(tmp_path: Path, args: list[str] | None = None) -> object:
    runner = CliRunner()
    return runner.invoke(cli, ["--db-path", str(tmp_path / "test.db")] + (args or []))


def test_show_empty(tmp_path: Path) -> None:
    result = _invoke(tmp_path)
    assert result.exit_code == 0
    assert "No tasks for today" in result.output


def test_add_and_show(tmp_path: Path) -> None:
    result = _invoke(tmp_path, ["add", "Buy groceries"])
    assert result.exit_code == 0
    assert "Added" in result.output

    result = _invoke(tmp_path)
    assert "Buy groceries" in result.output


def test_done(tmp_path: Path) -> None:
    _invoke(tmp_path, ["add", "Do laundry"])
    result = _invoke(tmp_path, ["done", "1"])
    assert result.exit_code == 0
    assert "Completed" in result.output


def test_done_invalid(tmp_path: Path) -> None:
    result = _invoke(tmp_path, ["done", "999"])
    assert "not found" in result.output


def test_remove(tmp_path: Path) -> None:
    _invoke(tmp_path, ["add", "Temporary task"])
    result = _invoke(tmp_path, ["remove", "1"])
    assert result.exit_code == 0
    assert "Removed" in result.output


def test_week_empty(tmp_path: Path) -> None:
    result = _invoke(tmp_path, ["week"])
    assert result.exit_code == 0
    assert "No tasks this week" in result.output


def test_week_with_tasks(tmp_path: Path) -> None:
    _invoke(tmp_path, ["add", "Monday task"])
    result = _invoke(tmp_path, ["week"])
    assert result.exit_code == 0
    assert "Monday task" in result.output


def test_morning_empty(tmp_path: Path) -> None:
    result = _invoke(tmp_path, ["morning"])
    assert result.exit_code == 0
    assert "Good morning" in result.output
    assert "No tasks" in result.output


def test_morning_with_tasks(tmp_path: Path) -> None:
    _invoke(tmp_path, ["add", "Morning task"])
    result = _invoke(tmp_path, ["morning"])
    assert result.exit_code == 0
    assert "Morning task" in result.output
    assert "pending" in result.output.lower()


def test_morning_shows_overdue(tmp_path: Path) -> None:
    # Add a task, then insert an old one directly
    _invoke(tmp_path, ["add", "Today task"])
    from planner import db as _db

    conn = _db.connect(Path(tmp_path / "test.db"))
    conn.execute(
        "INSERT INTO tasks (description, created_at) VALUES (?, ?)",
        ("Old task", "2026-03-20"),
    )
    conn.commit()
    conn.close()
    result = _invoke(tmp_path, ["morning"])
    assert "Old task" in result.output
    assert "overdue" in result.output.lower()


def test_focus_set(tmp_path: Path) -> None:
    _invoke(tmp_path, ["add", "Task A"])
    _invoke(tmp_path, ["add", "Task B"])
    result = _invoke(tmp_path, ["focus", "1", "2"])
    assert result.exit_code == 0
    assert "Focus set" in result.output


def test_focus_too_many(tmp_path: Path) -> None:
    for i in range(4):
        _invoke(tmp_path, ["add", f"Task {i}"])
    result = _invoke(tmp_path, ["focus", "1", "2", "3", "4"])
    assert result.exit_code == 0
    assert "at most 3" in result.output.lower()


def test_focus_shown_in_default_view(tmp_path: Path) -> None:
    _invoke(tmp_path, ["add", "Regular task"])
    _invoke(tmp_path, ["add", "Focus task"])
    _invoke(tmp_path, ["focus", "2"])
    result = _invoke(tmp_path)
    assert "Focus task" in result.output
    # Focus task should appear with a star marker
    assert "★" in result.output


# --- Priority & deadline CLI tests ---


def test_add_with_priority(tmp_path: Path) -> None:
    result = _invoke(tmp_path, ["add", "Urgent fix", "--priority", "high"])
    assert result.exit_code == 0
    assert "Added" in result.output


def test_add_with_due_date(tmp_path: Path) -> None:
    result = _invoke(tmp_path, ["add", "Ship feature", "--due", "2026-04-05"])
    assert result.exit_code == 0
    assert "Added" in result.output


def test_default_view_shows_priority_indicator(tmp_path: Path) -> None:
    _invoke(tmp_path, ["add", "Critical bug", "--priority", "high"])
    result = _invoke(tmp_path)
    assert "🔴" in result.output


def test_default_view_shows_due_date(tmp_path: Path) -> None:
    _invoke(tmp_path, ["add", "Deadline task", "--due", "2026-04-05"])
    result = _invoke(tmp_path)
    assert "2026-04-05" in result.output


def test_overdue_command_empty(tmp_path: Path) -> None:
    result = _invoke(tmp_path, ["overdue"])
    assert result.exit_code == 0
    assert "No overdue" in result.output


def test_overdue_command_shows_past_deadline(tmp_path: Path) -> None:
    from planner import db as _db

    conn = _db.connect(Path(tmp_path / "test.db"))
    conn.execute(
        "INSERT INTO tasks (description, created_at, due_date) VALUES (?, ?, ?)",
        ("Late task", "2026-03-25", "2026-03-28"),
    )
    conn.commit()
    conn.close()
    result = _invoke(tmp_path, ["overdue"])
    assert "Late task" in result.output


def test_morning_shows_due_today(tmp_path: Path) -> None:
    from planner import db as _db
    from datetime import date as _date

    conn = _db.connect(Path(tmp_path / "test.db"))
    today = _date.today().isoformat()
    conn.execute(
        "INSERT INTO tasks (description, created_at, due_date) VALUES (?, ?, ?)",
        ("Due now", today, today),
    )
    conn.commit()
    conn.close()
    result = _invoke(tmp_path, ["morning"])
    assert "Due now" in result.output
    assert "due today" in result.output.lower()


# --- Tag CLI tests ---


def test_add_with_tag(tmp_path: Path) -> None:
    result = _invoke(tmp_path, ["add", "Code task", "--tag", "code"])
    assert result.exit_code == 0
    assert "Added" in result.output


def test_add_with_multiple_tags(tmp_path: Path) -> None:
    result = _invoke(tmp_path, ["add", "Multi tag", "--tag", "code", "--tag", "urgent"])
    assert result.exit_code == 0
    result = _invoke(tmp_path)
    assert "code" in result.output
    assert "urgent" in result.output


def test_default_view_shows_tags(tmp_path: Path) -> None:
    _invoke(tmp_path, ["add", "Tagged item", "--tag", "work"])
    result = _invoke(tmp_path)
    assert "#work" in result.output


def test_tag_filter(tmp_path: Path) -> None:
    _invoke(tmp_path, ["add", "Code stuff", "--tag", "code"])
    _invoke(tmp_path, ["add", "Personal stuff", "--tag", "personal"])
    result = _invoke(tmp_path, ["tag", "code"])
    assert result.exit_code == 0
    assert "Code stuff" in result.output
    assert "Personal stuff" not in result.output


def test_tag_filter_empty(tmp_path: Path) -> None:
    result = _invoke(tmp_path, ["tag", "nonexistent"])
    assert result.exit_code == 0
    assert "No tasks" in result.output


def test_tags_list(tmp_path: Path) -> None:
    _invoke(tmp_path, ["add", "Task 1", "--tag", "code"])
    _invoke(tmp_path, ["add", "Task 2", "--tag", "code"])
    _invoke(tmp_path, ["add", "Task 3", "--tag", "personal"])
    result = _invoke(tmp_path, ["tags"])
    assert result.exit_code == 0
    assert "code" in result.output
    assert "2" in result.output
    assert "personal" in result.output


def test_tags_list_empty(tmp_path: Path) -> None:
    result = _invoke(tmp_path, ["tags"])
    assert result.exit_code == 0
    assert "No tags" in result.output


def test_morning_overdue_by_priority(tmp_path: Path) -> None:
    from planner import db as _db

    conn = _db.connect(Path(tmp_path / "test.db"))
    conn.execute(
        "INSERT INTO tasks (description, created_at, priority) VALUES (?, ?, ?)",
        ("Low prio", "2026-03-20", "low"),
    )
    conn.execute(
        "INSERT INTO tasks (description, created_at, priority) VALUES (?, ?, ?)",
        ("High prio", "2026-03-20", "high"),
    )
    conn.commit()
    conn.close()
    result = _invoke(tmp_path, ["morning"])
    # High should appear before Low in output
    high_pos = result.output.index("High prio")
    low_pos = result.output.index("Low prio")
    assert high_pos < low_pos


# --- Stats & streak CLI tests ---


def test_stats_empty(tmp_path: Path) -> None:
    result = _invoke(tmp_path, ["stats"])
    assert result.exit_code == 0
    assert "No tasks" in result.output


def test_stats_with_data(tmp_path: Path) -> None:
    _invoke(tmp_path, ["add", "Task 1"])
    _invoke(tmp_path, ["add", "Task 2"])
    _invoke(tmp_path, ["done", "1"])
    result = _invoke(tmp_path, ["stats"])
    assert result.exit_code == 0
    assert "2" in result.output  # total
    assert "1" in result.output  # completed
    assert "50" in result.output  # completion rate


def test_streak_empty(tmp_path: Path) -> None:
    result = _invoke(tmp_path, ["streak"])
    assert result.exit_code == 0
    assert "No tasks" in result.output


def test_streak_with_data(tmp_path: Path) -> None:
    from planner import db as _db

    conn = _db.connect(Path(tmp_path / "test.db"))
    # Two consecutive days, all tasks done
    conn.execute(
        "INSERT INTO tasks (description, created_at, done) VALUES (?, ?, 1)",
        ("Day1 task", "2026-03-30"),
    )
    conn.execute(
        "INSERT INTO tasks (description, created_at, done) VALUES (?, ?, 1)",
        ("Day2 task", "2026-03-31"),
    )
    conn.commit()
    conn.close()
    result = _invoke(tmp_path, ["streak"])
    assert result.exit_code == 0
    assert "🔥" in result.output


def test_streak_shows_today_progress(tmp_path: Path) -> None:
    _invoke(tmp_path, ["add", "Task A"])
    _invoke(tmp_path, ["add", "Task B"])
    _invoke(tmp_path, ["done", "1"])
    result = _invoke(tmp_path, ["streak"])
    assert "1/2" in result.output


# --- Edit, move, clear CLI tests ---


def test_edit_command(tmp_path: Path) -> None:
    _invoke(tmp_path, ["add", "Old name"])
    result = _invoke(tmp_path, ["edit", "1", "New name"])
    assert result.exit_code == 0
    assert "Updated" in result.output
    result = _invoke(tmp_path)
    assert "New name" in result.output


def test_edit_invalid(tmp_path: Path) -> None:
    result = _invoke(tmp_path, ["edit", "999", "Nope"])
    assert "not found" in result.output


def test_move_tomorrow(tmp_path: Path) -> None:
    _invoke(tmp_path, ["add", "Move me"])
    result = _invoke(tmp_path, ["move", "1", "tomorrow"])
    assert result.exit_code == 0
    assert "Moved" in result.output
    # Task should no longer appear today
    result = _invoke(tmp_path)
    assert "Move me" not in result.output


def test_move_date(tmp_path: Path) -> None:
    _invoke(tmp_path, ["add", "Move me"])
    result = _invoke(tmp_path, ["move", "1", "2026-04-10"])
    assert result.exit_code == 0
    assert "2026-04-10" in result.output


def test_clear_command(tmp_path: Path) -> None:
    _invoke(tmp_path, ["add", "Task 1"])
    _invoke(tmp_path, ["add", "Task 2"])
    _invoke(tmp_path, ["add", "Task 3"])
    _invoke(tmp_path, ["done", "1"])
    _invoke(tmp_path, ["done", "2"])
    result = _invoke(tmp_path, ["clear"])
    assert result.exit_code == 0
    assert "2" in result.output
    # Only pending task remains
    result = _invoke(tmp_path)
    assert "Task 3" in result.output


def test_clear_nothing(tmp_path: Path) -> None:
    _invoke(tmp_path, ["add", "Still pending"])
    result = _invoke(tmp_path, ["clear"])
    assert "No completed" in result.output
