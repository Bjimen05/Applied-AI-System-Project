from __future__ import annotations
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    title: str
    description: str
    duration_minutes: int
    priority: str          # "high", "medium", or "low"
    due_time: str          # e.g. "09:00"
    completed: bool = False

    def mark_complete(self) -> None:
        pass

    def priority_rank(self) -> int:
        pass

    def __repr__(self) -> str:
        pass


# ---------------------------------------------------------------------------
# Pet 
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    name: str
    species: str
    breed: str
    age: int
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        pass

    def remove_task(self, title: str) -> None:
        pass

    def list_tasks(self) -> list[Task]:
        pass

    def get_pending_tasks(self) -> list[Task]:
        pass

    def __repr__(self) -> str:
        pass


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    name: str
    available_minutes: int
    day_start: str         # e.g. "08:00"
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        pass

    def remove_pet(self, name: str) -> None:
        pass

    def list_pets(self) -> list[Pet]:
        pass

    def get_all_tasks(self) -> list[tuple[Pet, Task]]:
        pass

    def __repr__(self) -> str:
        pass


# ---------------------------------------------------------------------------
# ScheduledEntry
# ---------------------------------------------------------------------------

@dataclass
class ScheduledEntry:
    pet: Pet
    task: Task
    start_time: str
    end_time: str

    def __repr__(self) -> str:
        pass


# ---------------------------------------------------------------------------
# DailyPlan
# ---------------------------------------------------------------------------

class DailyPlan:
    def __init__(self, owner: Owner, entries: list[ScheduledEntry],
                 skipped_tasks: list[tuple[Pet, Task]]) -> None:
        self.owner = owner
        self.entries = entries
        self.skipped_tasks = skipped_tasks

    def display(self) -> str:
        pass

    def explain(self) -> str:
        pass

    def total_time_used(self) -> int:
        pass


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    def collect_tasks(self) -> list[tuple[Pet, Task]]:
        pass

    def generate_plan(self) -> DailyPlan:
        pass

    def _sort_tasks(self, tasks: list[tuple[Pet, Task]]) -> list[tuple[Pet, Task]]:
        pass
