from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta

import click
from rich.console import Console
from rich.table import Table

from planner import db
from planner.models import Priority

console = Console()

_PRIORITY_INDICATOR = {
    Priority.HIGH: "🔴",
    Priority.MEDIUM: "🟡",
    Priority.LOW: "🟢",
}


def _get_conn(ctx: click.Context) -> sqlite3.Connection:
    if "conn" not in ctx.obj:
        ctx.obj["conn"] = db.connect(ctx.obj["db_path"])
    return ctx.obj["conn"]


@click.group(invoke_without_command=True)
@click.option("--db-path", default=None, hidden=True, help="Override database path.")
@click.pass_context
def cli(ctx: click.Context, db_path: str | None) -> None:
    """A simple daily task planner."""
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db.Path(db_path) if db_path else db.DEFAULT_DB
    if ctx.invoked_subcommand is None:
        _show_today(ctx)


def _show_today(ctx: click.Context) -> None:
    conn = _get_conn(ctx)
    tasks = db.get_tasks_for_date(conn, date.today())
    if not tasks:
        console.print("[dim]No tasks for today. Use [bold]plan add[/bold] to create one.[/dim]")
        return
    focus_ids = db.get_focus_ids(conn, date.today())
    focus_tasks = [t for t in tasks if t.id in focus_ids]
    other_tasks = [t for t in tasks if t.id not in focus_ids]
    table = Table(title=f"Tasks for {date.today()}")
    table.add_column("ID", style="dim")
    table.add_column("P")
    table.add_column("Task")
    table.add_column("Tags")
    table.add_column("Due")
    table.add_column("Status")
    for t in focus_tasks + other_tasks:
        status = "[green]done[/green]" if t.done else "[yellow]pending[/yellow]"
        prefix = "★ " if t.id in focus_ids else ""
        desc = f"[s]{t.description}[/s]" if t.done else t.description
        due_str = str(t.due_date) if t.due_date else ""
        tags_str = " ".join(f"[magenta]#{tag}[/magenta]" for tag in t.tags)
        style = "bold cyan" if t.id in focus_ids else None
        table.add_row(str(t.id), _PRIORITY_INDICATOR[t.priority], f"{prefix}{desc}", tags_str, due_str, status, style=style)
    console.print(table)


@cli.command()
@click.argument("description")
@click.option("--priority", "-p", type=click.Choice(["high", "medium", "low"]), default="medium", help="Task priority.")
@click.option("--due", type=click.DateTime(formats=["%Y-%m-%d"]), default=None, help="Due date (YYYY-MM-DD).")
@click.option("--tag", "-t", multiple=True, help="Tag for the task (repeatable).")
@click.pass_context
def add(ctx: click.Context, description: str, priority: str, due: datetime | None, tag: tuple[str, ...]) -> None:
    """Add a new task for today."""
    conn = _get_conn(ctx)
    task = db.add_task(
        conn,
        description,
        priority=Priority(priority),
        due_date=due.date() if due else None,
        tags=list(tag) if tag else None,
    )
    console.print(f"[green]Added:[/green] #{task.id} — {task.description}")


@cli.command()
@click.argument("task_id", type=int)
@click.pass_context
def done(ctx: click.Context, task_id: int) -> None:
    """Mark a task as complete."""
    conn = _get_conn(ctx)
    if db.complete_task(conn, task_id):
        console.print(f"[green]Completed:[/green] #{task_id}")
    else:
        console.print(f"[red]Task #{task_id} not found or already done.[/red]")


@cli.command()
@click.argument("task_id", type=int)
@click.pass_context
def remove(ctx: click.Context, task_id: int) -> None:
    """Delete a task."""
    conn = _get_conn(ctx)
    if db.remove_task(conn, task_id):
        console.print(f"[green]Removed:[/green] #{task_id}")
    else:
        console.print(f"[red]Task #{task_id} not found.[/red]")


@cli.command()
@click.pass_context
def morning(ctx: click.Context) -> None:
    """Show a morning briefing with today's tasks and overdue items."""
    conn = _get_conn(ctx)
    today = date.today()
    day_name = today.strftime("%A")
    console.print(f"\n[bold]Good morning![/bold] Today is [cyan]{day_name}, {today}[/cyan]\n")

    overdue = db.get_overdue_tasks(conn, today)
    today_tasks = db.get_tasks_for_date(conn, today)
    due_today = db.get_tasks_due_on(conn, today)

    if overdue:
        console.print(f"[bold red]Overdue ({len(overdue)}):[/bold red]")
        for t in overdue:
            indicator = _PRIORITY_INDICATOR[t.priority]
            console.print(f"  {indicator} [red]#{t.id}[/red] {t.description} [dim](from {t.created_at})[/dim]")
        console.print()

    if due_today:
        console.print(f"[bold yellow]Due today ({len(due_today)}):[/bold yellow]")
        for t in due_today:
            indicator = _PRIORITY_INDICATOR[t.priority]
            console.print(f"  {indicator} #{t.id} {t.description}")
        console.print()

    if today_tasks:
        pending = [t for t in today_tasks if not t.done]
        done_list = [t for t in today_tasks if t.done]
        console.print(f"[bold]Today's tasks:[/bold] {len(pending)} pending, {len(done_list)} done")
        for t in today_tasks:
            status = "[green]✓[/green]" if t.done else "[yellow]○[/yellow]"
            indicator = _PRIORITY_INDICATOR[t.priority]
            console.print(f"  {status} {indicator} #{t.id} {t.description}")
    else:
        console.print("[dim]No tasks for today yet.[/dim]")

    console.print()


@cli.command()
@click.argument("task_ids", nargs=-1, type=int, required=True)
@click.pass_context
def focus(ctx: click.Context, task_ids: tuple[int, ...]) -> None:
    """Pick up to 3 focus tasks for today. Usage: plan focus 1 3 5"""
    conn = _get_conn(ctx)
    ids = list(task_ids)
    if len(ids) > 3:
        console.print("[red]You can focus on at most 3 tasks per day.[/red]")
        return
    try:
        focused = db.set_focus(conn, ids, date.today())
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        return
    names = ", ".join(f"#{t.id} {t.description}" for t in focused)
    console.print(f"[green]Focus set:[/green] {names}")


@cli.command()
@click.argument("tag_name")
@click.pass_context
def tag(ctx: click.Context, tag_name: str) -> None:
    """Show tasks with a specific tag."""
    conn = _get_conn(ctx)
    tasks = db.get_tasks_by_tag(conn, tag_name)
    if not tasks:
        console.print(f"[dim]No tasks with tag [bold]#{tag_name}[/bold].[/dim]")
        return
    table = Table(title=f"Tasks tagged #{tag_name}")
    table.add_column("ID", style="dim")
    table.add_column("P")
    table.add_column("Task")
    table.add_column("Tags")
    table.add_column("Status")
    for t in tasks:
        status = "[green]done[/green]" if t.done else "[yellow]pending[/yellow]"
        tags_str = " ".join(f"[magenta]#{tg}[/magenta]" for tg in t.tags)
        table.add_row(str(t.id), _PRIORITY_INDICATOR[t.priority], t.description, tags_str, status)
    console.print(table)


@cli.command()
@click.pass_context
def tags(ctx: click.Context) -> None:
    """List all tags with task counts."""
    conn = _get_conn(ctx)
    tag_counts = db.get_all_tags(conn)
    if not tag_counts:
        console.print("[dim]No tags yet.[/dim]")
        return
    table = Table(title="Tags")
    table.add_column("Tag")
    table.add_column("Tasks", justify="right")
    for tag_name, count in tag_counts:
        table.add_row(f"[magenta]#{tag_name}[/magenta]", str(count))
    console.print(table)


@cli.command()
@click.pass_context
def overdue(ctx: click.Context) -> None:
    """Show all tasks past their deadline."""
    conn = _get_conn(ctx)
    tasks = db.get_past_deadline_tasks(conn, date.today())
    if not tasks:
        console.print("[green]No overdue tasks![/green]")
        return
    table = Table(title="Overdue Tasks")
    table.add_column("ID", style="dim")
    table.add_column("P")
    table.add_column("Task")
    table.add_column("Due Date", style="red")
    for t in tasks:
        table.add_row(str(t.id), _PRIORITY_INDICATOR[t.priority], t.description, str(t.due_date))
    console.print(table)


@cli.command()
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Show productivity stats."""
    conn = _get_conn(ctx)
    all_tasks = db.get_all_tasks(conn)
    if not all_tasks:
        console.print("[dim]No tasks yet.[/dim]")
        return

    total = len(all_tasks)
    completed = sum(1 for t in all_tasks if t.done)
    pending = total - completed
    rate = round(completed / total * 100)

    daily = db.get_daily_completion(conn)
    days_with_tasks = len(daily)
    avg_per_day = round(completed / days_with_tasks, 1) if days_with_tasks else 0

    # Most productive weekday
    weekday_counts: dict[str, int] = {}
    for day_str, _, done_count in daily:
        day_obj = date.fromisoformat(day_str)
        name = day_obj.strftime("%A")
        weekday_counts[name] = weekday_counts.get(name, 0) + done_count
    best_day = max(weekday_counts, key=weekday_counts.get) if weekday_counts else "N/A"

    # Current streak
    current_streak = _calc_streak(daily, current_only=True)

    console.print("\n[bold]Productivity Stats[/bold]\n")
    console.print(f"  Total tasks:       {total}")
    console.print(f"  Completed:         [green]{completed}[/green]")
    console.print(f"  Pending:           [yellow]{pending}[/yellow]")
    console.print(f"  Completion rate:   [bold]{rate}%[/bold]")
    console.print(f"  Avg completed/day: {avg_per_day}")
    console.print(f"  Most productive:   [cyan]{best_day}[/cyan]")
    console.print(f"  Current streak:    🔥 {current_streak} day{'s' if current_streak != 1 else ''}")
    console.print()


@cli.command()
@click.pass_context
def streak(ctx: click.Context) -> None:
    """Show your completion streak."""
    conn = _get_conn(ctx)
    daily = db.get_daily_completion(conn)
    if not daily:
        console.print("[dim]No tasks yet.[/dim]")
        return

    current = _calc_streak(daily, current_only=True)
    longest = _calc_streak(daily, current_only=False)

    today_tasks = db.get_tasks_for_date(conn, date.today())
    today_done = sum(1 for t in today_tasks if t.done)
    today_total = len(today_tasks)

    console.print(f"\n🔥 Current streak: [bold]{current}[/bold] day{'s' if current != 1 else ''}")
    console.print(f"🏆 Longest streak: [bold]{longest}[/bold] day{'s' if longest != 1 else ''}")
    if today_total:
        console.print(f"📋 Today: [bold]{today_done}/{today_total}[/bold] tasks done")
    else:
        console.print("[dim]No tasks for today yet.[/dim]")
    console.print()


def _calc_streak(daily: list[tuple[str, int, int]], *, current_only: bool) -> int:
    if current_only:
        streak = 0
        for day_str, total, done in reversed(daily):
            if total == done:
                streak += 1
            else:
                break
        return streak
    else:
        longest = 0
        current = 0
        for _, total, done in daily:
            if total == done:
                current += 1
                longest = max(longest, current)
            else:
                current = 0
        return longest


@cli.command()
@click.pass_context
def week(ctx: click.Context) -> None:
    """Show a weekly summary."""
    conn = _get_conn(ctx)
    today = date.today()
    start = today - timedelta(days=today.weekday())  # Monday
    tasks = db.get_tasks_between(conn, start, today)
    if not tasks:
        console.print("[dim]No tasks this week.[/dim]")
        return
    total = len(tasks)
    completed = sum(1 for t in tasks if t.done)
    table = Table(title=f"Week of {start} — {today}")
    table.add_column("ID", style="dim")
    table.add_column("Date")
    table.add_column("Task")
    table.add_column("Status")
    for t in tasks:
        status = "[green]done[/green]" if t.done else "[yellow]pending[/yellow]"
        table.add_row(str(t.id), str(t.created_at), t.description, status)
    console.print(table)
    console.print(f"\n[bold]{completed}/{total}[/bold] tasks completed")
