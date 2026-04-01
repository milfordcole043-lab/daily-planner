from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class Task:
    id: int
    description: str
    created_at: date
    done: bool = False
    done_at: datetime | None = None
