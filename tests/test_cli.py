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
