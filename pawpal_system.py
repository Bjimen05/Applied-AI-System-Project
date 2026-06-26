from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Priority enum — prevents silent typos like priority="hihg"
# ---------------------------------------------------------------------------

class Priority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    title: str
    description: str
    duration_minutes: int
    priority: Priority
    due_time: int           # minutes since midnight, e.g. 540 = 09:00
    completed: bool = False

    def mark_complete(self) -> None:
        self.completed = True

    def priority_rank(self) -> int:
        return self.priority.value


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

    def remove_task(self, task: Task) -> None:
        # removes by object identity — avoids duplicate-title ambiguity
        pass

    def list_tasks(self) -> list[Task]:
        pass

    def get_pending_tasks(self) -> list[Task]:
        pass


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    name: str
    available_minutes: int
    day_start: int          # minutes since midnight, e.g. 480 = 08:00
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        pass

    def remove_pet(self, name: str) -> None:
        pass

    def list_pets(self) -> list[Pet]:
        pass

    def get_all_tasks(self) -> list[tuple[Pet, Task]]:
        pass


# ---------------------------------------------------------------------------
# ScheduledEntry
# ---------------------------------------------------------------------------

@dataclass
class ScheduledEntry:
    pet: Pet
    task: Task
    start_time: int         # minutes since midnight
    end_time: int           # minutes since midnight


# ---------------------------------------------------------------------------
# DailyPlan
# ---------------------------------------------------------------------------

class DailyPlan:
    def __init__(self, owner: Owner, date: str,
                 entries: list[ScheduledEntry],
                 skipped_tasks: list[tuple[Pet, Task]]) -> None:
        self.owner = owner
        self.date = date
        self.entries = entries
        self.skipped_tasks = skipped_tasks

    def display(self) -> str:
        pass

    def explain(self) -> str:
        pass

    def total_time_used(self) -> int:
        return sum(e.task.duration_minutes for e in self.entries)


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    def collect_tasks(self) -> list[tuple[Pet, Task]]:
        # delegates to owner.get_all_tasks() which flattens across all pets
        pass

    def generate_plan(self) -> DailyPlan:
        # time anchor: self.owner.day_start (minutes since midnight)
        # time budget: self.owner.available_minutes
        pass

    def _sort_tasks(self, tasks: list[tuple[Pet, Task]]) -> list[tuple[Pet, Task]]:
        # primary: priority_rank() ascending (HIGH=1 first)
        # secondary: due_time ascending (earlier deadlines first)
        # tertiary: duration_minutes ascending (fit more tasks in budget)
        pass
