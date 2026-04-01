# daily-planner

A simple CLI daily task planner with priorities, deadlines, tags, and streaks.

## Features

**Task Management** — add, edit, move, complete, remove, and clear tasks.

**Organization** — priority levels (high/medium/low), due dates, tags, and daily focus tasks.

**Insights** — morning briefings, overdue tracking, productivity stats, and completion streaks.

## Tech Stack

- Python 3.12
- [Click](https://click.palletsprojects.com/) — CLI framework
- [Rich](https://rich.readthedocs.io/) — terminal formatting
- SQLite — local storage
- pytest — testing (73/73 passing)

## Installation

```bash
git clone https://github.com/milfordcole043-lab/daily-planner.git
cd daily-planner
pip install -e .
```

## Quick Start

```bash
# Add a high-priority task with a deadline and tag
plan add "Fix login bug" --priority high --due 2026-04-05 --tag backend

# Start your day with a briefing
plan morning

# Check your streak
plan streak
```

## Commands

| Command | Description |
|---------|-------------|
| `plan` | Show today's tasks |
| `plan add "task"` | Add a task (`--priority`, `--due`, `--tag`) |
| `plan done <id>` | Mark a task as complete |
| `plan edit <id> "text"` | Rename a task |
| `plan move <id> <date>` | Reschedule (`tomorrow` or `YYYY-MM-DD`) |
| `plan remove <id>` | Delete a task |
| `plan clear` | Remove all completed tasks |
| `plan focus <ids>` | Set up to 3 focus tasks for today |
| `plan morning` | Morning briefing with overdue and due-today |
| `plan week` | Weekly summary |
| `plan overdue` | Tasks past their deadline |
| `plan tag <name>` | Filter tasks by tag |
| `plan tags` | List all tags with counts |
| `plan stats` | Productivity statistics |
| `plan streak` | Completion streak tracker |

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

```
============================= 73 passed ==============================
```

## License

MIT
