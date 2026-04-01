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
