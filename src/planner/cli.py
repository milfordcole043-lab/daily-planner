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
    table = Table(title=f"Tasks for {date.today()}")
    table.add_column("ID", style="dim")
    table.add_column("Task")
    table.add_column("Status")
    for t in tasks:
        status = "[green]done[/green]" if t.done else "[yellow]pending[/yellow]"
        desc = f"[s]{t.description}[/s]" if t.done else t.description
        table.add_row(str(t.id), desc, status)
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
