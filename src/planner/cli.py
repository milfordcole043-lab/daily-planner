from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import click
from rich.console import Console
from rich.table import Table

from planner import db

console = Console()


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
    table.add_column("Task")
    table.add_column("Status")
    for t in focus_tasks + other_tasks:
        status = "[green]done[/green]" if t.done else "[yellow]pending[/yellow]"
        prefix = "★ " if t.id in focus_ids else ""
        desc = f"[s]{t.description}[/s]" if t.done else t.description
        style = "bold cyan" if t.id in focus_ids else None
        table.add_row(str(t.id), f"{prefix}{desc}", status, style=style)
    console.print(table)


@cli.command()
@click.argument("description")
@click.pass_context
def add(ctx: click.Context, description: str) -> None:
    """Add a new task for today."""
    conn = _get_conn(ctx)
    task = db.add_task(conn, description)
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

    if overdue:
        console.print(f"[bold red]Overdue ({len(overdue)}):[/bold red]")
        for t in overdue:
            console.print(f"  [red]#{t.id}[/red] {t.description} [dim](from {t.created_at})[/dim]")
        console.print()

    if today_tasks:
        pending = [t for t in today_tasks if not t.done]
        done = [t for t in today_tasks if t.done]
        console.print(f"[bold]Today's tasks:[/bold] {len(pending)} pending, {len(done)} done")
        for t in today_tasks:
            status = "[green]✓[/green]" if t.done else "[yellow]○[/yellow]"
            console.print(f"  {status} #{t.id} {t.description}")
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
