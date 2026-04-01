from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Task:
    id: int
    description: str
    created_at: date
    done: bool = False
    done_at: datetime | None = None
    priority: Priority = Priority.MEDIUM
    due_date: date | None = None
