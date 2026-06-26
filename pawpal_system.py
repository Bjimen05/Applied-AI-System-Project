from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
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
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        self.tasks.remove(task)

    def list_tasks(self) -> list[Task]:
        return list(self.tasks)

    def get_pending_tasks(self) -> list[Task]:
        return [t for t in self.tasks if not t.completed]


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
        self.pets.append(pet)

    def remove_pet(self, name: str) -> None:
        self.pets = [p for p in self.pets if p.name != name]

    def list_pets(self) -> list[Pet]:
        return list(self.pets)

    def get_all_tasks(self) -> list[tuple[Pet, Task]]:
        return [(pet, task) for pet in self.pets for task in pet.get_pending_tasks()]


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
# Helper
# ---------------------------------------------------------------------------

def _fmt_time(minutes: int) -> str:
    """Convert minutes-since-midnight to HH:MM string."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


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
        lines = [
            f"Daily Plan for {self.owner.name} — {self.date}",
            "─" * 50,
        ]

        if not self.entries:
            lines.append("  No tasks scheduled.")
        else:
            for e in self.entries:
                start = _fmt_time(e.start_time)
                end   = _fmt_time(e.end_time)
                lines.append(
                    f"  {start} – {end}  "
                    f"{e.pet.name:<12} "
                    f"{e.task.title} ({e.task.duration_minutes} min) "
                    f"[{e.task.priority.name}]"
                )

        lines.append("─" * 50)
        lines.append(
            f"  Total: {self.total_time_used()} / {self.owner.available_minutes} min used"
        )

        if self.skipped_tasks:
            skipped_titles = ", ".join(t.title for _, t in self.skipped_tasks)
            lines.append(f"  Skipped ({len(self.skipped_tasks)}): {skipped_titles}")

        return "\n".join(lines)

    def explain(self) -> str:
        lines = [
            f"Scheduling reasoning for {self.owner.name} — {self.date}",
            "",
        ]

        if self.entries:
            lines.append(f"Scheduled ({len(self.entries)} tasks):")
            for e in self.entries:
                lines.append(
                    f"  + {e.task.title} ({e.pet.name}) — "
                    f"{e.task.priority.name} priority, "
                    f"due {_fmt_time(e.task.due_time)}, "
                    f"scheduled at {_fmt_time(e.start_time)}"
                )

        if self.skipped_tasks:
            remaining = self.owner.available_minutes - self.total_time_used()
            lines.append("")
            lines.append(f"Skipped ({len(self.skipped_tasks)} tasks):")
            for pet, task in self.skipped_tasks:
                lines.append(
                    f"  - {task.title} ({pet.name}) — "
                    f"{task.priority.name} priority, "
                    f"{task.duration_minutes} min needed but only {remaining} min remaining"
                )

        return "\n".join(lines)

    def total_time_used(self) -> int:
        return sum(e.task.duration_minutes for e in self.entries)


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    def collect_tasks(self) -> list[tuple[Pet, Task]]:
        return self.owner.get_all_tasks()

    def generate_plan(self) -> DailyPlan:
        sorted_tasks = self._sort_tasks(self.collect_tasks())

        clock = self.owner.day_start          # running time cursor
        budget = self.owner.available_minutes
        time_used = 0
        entries: list[ScheduledEntry] = []
        skipped: list[tuple[Pet, Task]] = []

        for pet, task in sorted_tasks:
            if time_used + task.duration_minutes <= budget:
                entries.append(ScheduledEntry(
                    pet=pet,
                    task=task,
                    start_time=clock,
                    end_time=clock + task.duration_minutes,
                ))
                clock += task.duration_minutes
                time_used += task.duration_minutes
            else:
                skipped.append((pet, task))

        return DailyPlan(
            owner=self.owner,
            date=str(date.today()),
            entries=entries,
            skipped_tasks=skipped,
        )

    def _sort_tasks(self, tasks: list[tuple[Pet, Task]]) -> list[tuple[Pet, Task]]:
        # 1st: priority (HIGH=1 sorts before LOW=3)
        # 2nd: due_time (earlier deadlines first within same priority)
        # 3rd: duration (shorter tasks first to fit more into the budget)
        return sorted(tasks, key=lambda pt: (
            pt[1].priority_rank(),
            pt[1].due_time,
            pt[1].duration_minutes,
        ))
