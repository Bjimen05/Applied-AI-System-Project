from __future__ import annotations
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from enum import Enum
import json
from pathlib import Path

from marshmallow import Schema, fields as mf, post_load, EXCLUDE


# ---------------------------------------------------------------------------
# Priority enum — prevents silent typos like priority="hihg"
# ---------------------------------------------------------------------------

class Priority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3


# ---------------------------------------------------------------------------
# Frequency enum — controls whether a completed task recurs
# ---------------------------------------------------------------------------

class Frequency(Enum):
    ONCE   = "once"    # no recurrence — default
    DAILY  = "daily"   # next occurrence is due_date + 1 day
    WEEKLY = "weekly"  # next occurrence is due_date + 7 days


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    title: str
    description: str
    duration_minutes: int
    priority: Priority
    due_time: int                                        # minutes since midnight, e.g. 540 = 09:00
    completed: bool = False
    frequency: Frequency = Frequency.ONCE
    due_date: date = field(default_factory=date.today)  # calendar date this instance is due

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True

    def priority_rank(self) -> int:
        """Return numeric sort key: HIGH=1, MEDIUM=2, LOW=3."""
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
        """Append a task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a task by object reference."""
        self.tasks.remove(task)

    def list_tasks(self) -> list[Task]:
        """Return a shallow copy of all tasks (completed and pending)."""
        return list(self.tasks)

    def get_pending_tasks(self) -> list[Task]:
        """Return only tasks that have not been completed."""
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
        """Add a pet to this owner's household."""
        self.pets.append(pet)

    def remove_pet(self, name: str) -> None:
        """Remove the first pet whose name matches."""
        self.pets = [p for p in self.pets if p.name != name]

    def list_pets(self) -> list[Pet]:
        """Return a shallow copy of the owner's pet list."""
        return list(self.pets)

    def get_all_tasks(self) -> list[tuple[Pet, Task]]:
        """Return all pending tasks across every pet as (Pet, Task) pairs."""
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

# Skip reasons for skipped tasks
SKIP_BUDGET = "budget"
SKIP_DEADLINE = "deadline"


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
                 skipped_tasks: list[tuple[Pet, Task, str]]) -> None:
        self.owner = owner
        self.date = date
        self.entries = entries
        self.skipped_tasks = skipped_tasks
        self._total_cached: int | None = None

    def display(self) -> str:
        """Return a formatted schedule string showing all entries and skipped tasks."""
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
            skipped_titles = ", ".join(t.title for _, t, _ in self.skipped_tasks)
            lines.append(f"  Skipped ({len(self.skipped_tasks)}): {skipped_titles}")

        return "\n".join(lines)

    def explain(self) -> str:
        """Return a plain-English explanation of why each task was scheduled or skipped."""
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
            for pet, task, reason in self.skipped_tasks:
                if reason == SKIP_DEADLINE:
                    lines.append(
                        f"  - {task.title} ({pet.name}) — "
                        f"{task.priority.name} priority, "
                        f"missed deadline ({_fmt_time(task.due_time)}): "
                        f"would finish after due time"
                    )
                else:
                    lines.append(
                        f"  - {task.title} ({pet.name}) — "
                        f"{task.priority.name} priority, "
                        f"{task.duration_minutes} min needed but only {remaining} min remaining"
                    )

        return "\n".join(lines)

    def total_time_used(self) -> int:
        """Return the sum of all scheduled task durations in minutes."""
        if self._total_cached is None:
            self._total_cached = sum(e.task.duration_minutes for e in self.entries)
        return self._total_cached


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    def collect_tasks(self) -> list[tuple[Pet, Task]]:
        """Retrieve all pending tasks across the owner's pets."""
        return self.owner.get_all_tasks()

    def collect_all_tasks(self) -> list[tuple[Pet, Task]]:
        """Retrieve every task (pending and completed) across the owner's pets."""
        return [(pet, task) for pet in self.owner.pets for task in pet.list_tasks()]

    def mark_task_complete(self, pet: Pet, task: Task) -> Task | None:
        """Mark a task complete and, for recurring tasks, add the next occurrence to the pet.

        Uses timedelta to calculate the next due_date:
          - Frequency.DAILY  → due_date + timedelta(days=1)
          - Frequency.WEEKLY → due_date + timedelta(days=7)
          - Frequency.ONCE   → no new task; returns None

        Returns the newly created Task for DAILY/WEEKLY, or None for ONCE.
        """
        task.mark_complete()

        if task.frequency == Frequency.ONCE:
            return None

        days_ahead = 1 if task.frequency == Frequency.DAILY else 7
        next_due_date = task.due_date + timedelta(days=days_ahead)

        next_task = replace(task, due_date=next_due_date, completed=False)
        pet.add_task(next_task)
        return next_task

    def sort_by_time(self, tasks: list[tuple[Pet, Task]]) -> list[tuple[Pet, Task]]:
        """Return tasks sorted by due_time (minutes since midnight) ascending.

        Sorts directly on the integer due_time value — earlier deadlines first.
        """
        return sorted(tasks, key=lambda pt: pt[1].due_time)

    def filter_tasks(
        self,
        tasks: list[tuple[Pet, Task]],
        *,
        completed: bool | None = None,
        pet_name: str | None = None,
    ) -> list[tuple[Pet, Task]]:
        """Return a filtered subset of tasks.

        Args:
            tasks:      List of (Pet, Task) pairs to filter.
            completed:  If True, keep only completed tasks.
                        If False, keep only pending tasks.
                        If None, completion status is not filtered.
            pet_name:   If given, keep only tasks belonging to this pet (case-insensitive).
                        If None, all pets are included.

        Both filters are applied together when both are provided.
        """
        return [
            (pet, task) for pet, task in tasks
            if (completed is None or task.completed == completed)
            and (pet_name is None or pet.name.lower() == pet_name.lower())
        ]

    def detect_conflicts(self, tasks: list[tuple[Pet, Task]]) -> list[str]:
        """Check every pair of pending tasks for overlapping ideal time windows.

        Each task's ideal window is [due_time - duration_minutes, due_time].
        Two tasks conflict when those windows intersect — meaning both tasks
        would need to be in progress at the same moment to meet their deadlines.

        Returns a list of warning strings (one per conflicting pair).
        An empty list means no conflicts were found.
        """
        warnings: list[str] = []
        pending = [(pet, task) for pet, task in tasks if not task.completed]

        for i, (pet_a, task_a) in enumerate(pending):
            start_a = task_a.due_time - task_a.duration_minutes
            for pet_b, task_b in pending[i + 1:]:
                start_b = task_b.due_time - task_b.duration_minutes
                overlaps = start_a < task_b.due_time and start_b < task_a.due_time
                if overlaps:
                    warnings.append(
                        f"WARNING: '{task_a.title}' ({pet_a.name}) "
                        f"[{_fmt_time(start_a)}-{_fmt_time(task_a.due_time)}] "
                        f"overlaps with '{task_b.title}' ({pet_b.name}) "
                        f"[{_fmt_time(start_b)}-{_fmt_time(task_b.due_time)}]"
                    )

        return warnings

    def generate_plan(self) -> DailyPlan:
        """Build a greedy daily plan, fitting tasks into the owner's time budget."""
        sorted_tasks = self._sort_tasks(self.collect_tasks())

        clock = self.owner.day_start          # running time cursor
        budget = self.owner.available_minutes
        time_used = 0
        entries: list[ScheduledEntry] = []
        skipped: list[tuple[Pet, Task, str]] = []

        for pet, task in sorted_tasks:
            finish_time = clock + task.duration_minutes
            # Deadline check: task must finish by its due_time
            if finish_time > task.due_time:
                skipped.append((pet, task, SKIP_DEADLINE))
                continue
            # Budget check: owner must have enough time remaining
            if time_used + task.duration_minutes > budget:
                skipped.append((pet, task, SKIP_BUDGET))
                continue
            entries.append(ScheduledEntry(
                pet=pet,
                task=task,
                start_time=clock,
                end_time=finish_time,
            ))
            clock += task.duration_minutes
            time_used += task.duration_minutes

        return DailyPlan(
            owner=self.owner,
            date=str(date.today()),
            entries=entries,
            skipped_tasks=skipped,
        )

    def score_task(self, task: Task) -> float:
        """Compute a weighted priority score that combines three signals.

        Score = priority base + urgency bonus + efficiency bonus

        - Priority base: HIGH=30, MEDIUM=20, LOW=10
        - Urgency bonus (0–10): tasks whose deadline is closer to day_start
          score higher, normalized over an 8-hour window
        - Efficiency bonus (0–5): shorter tasks score slightly higher,
          so when two tasks tie on priority and urgency the one that
          consumes less of the budget is preferred

        Higher score → scheduled sooner by sort_by_weight.
        """
        base = {Priority.HIGH: 30.0, Priority.MEDIUM: 20.0, Priority.LOW: 10.0}[task.priority]

        window_minutes = 480  # normalize urgency over an 8-hour day
        minutes_until_due = max(task.due_time - self.owner.day_start, 0)
        urgency_bonus = max(0.0, (window_minutes - minutes_until_due) / window_minutes) * 10.0

        efficiency_bonus = max(0.0, (60 - task.duration_minutes) / 60) * 5.0

        return base + urgency_bonus + efficiency_bonus

    def sort_by_weight(self, tasks: list[tuple[Pet, Task]]) -> list[tuple[Pet, Task]]:
        """Return tasks sorted by weighted priority score descending (highest first).

        Uses score_task to blend priority, urgency, and duration efficiency into
        a single float, giving more nuanced ordering than a fixed enum rank.
        Pending and completed tasks are both accepted; score applies to all.
        """
        return sorted(tasks, key=lambda pt: self.score_task(pt[1]), reverse=True)

    def _sort_tasks(self, tasks: list[tuple[Pet, Task]]) -> list[tuple[Pet, Task]]:
        """Sort tasks by urgency-adjusted priority, then due time, then duration.

        A task due within 60 minutes of day_start is considered urgent and gets
        its priority rank boosted by one tier (e.g. MEDIUM acts like HIGH).
        """
        urgency_window = self.owner.day_start + 60

        def sort_key(pt: tuple[Pet, Task]) -> tuple[int, int, int]:
            task = pt[1]
            rank = task.priority_rank()
            # Boost urgent tasks: decrement rank so they sort earlier
            if task.due_time <= urgency_window and rank > 1:
                rank -= 1
            return (rank, task.due_time, task.duration_minutes)

        return sorted(tasks, key=sort_key)


# ---------------------------------------------------------------------------
# Marshmallow schemas — serialization / deserialization
# ---------------------------------------------------------------------------

class TaskSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    title            = mf.Str()
    description      = mf.Str()
    duration_minutes = mf.Int()
    priority         = mf.Enum(Priority, by_value=False)   # serializes as "HIGH" / "MEDIUM" / "LOW"
    due_time         = mf.Int()
    completed        = mf.Bool()
    frequency        = mf.Enum(Frequency, by_value=True)   # serializes as "once" / "daily" / "weekly"
    due_date         = mf.Date(format="%Y-%m-%d")

    @post_load
    def make_task(self, data: dict, **_kwargs) -> Task:
        return Task(**data)


class PetSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name    = mf.Str()
    species = mf.Str()
    breed   = mf.Str()
    age     = mf.Int()
    tasks   = mf.List(mf.Nested(TaskSchema))

    @post_load
    def make_pet(self, data: dict, **_kwargs) -> Pet:
        tasks = data.pop("tasks", [])
        pet = Pet(**data)
        for t in tasks:
            pet.add_task(t)
        return pet


class OwnerSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name              = mf.Str()
    available_minutes = mf.Int()
    day_start         = mf.Int()
    pets              = mf.List(mf.Nested(PetSchema))

    @post_load
    def make_owner(self, data: dict, **_kwargs) -> Owner:
        pets = data.pop("pets", [])
        owner = Owner(**data)
        for p in pets:
            owner.add_pet(p)
        return owner


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

_owner_schema = OwnerSchema()


def save_to_json(owner: Owner, path: str | Path = "data.json") -> None:
    """Serialize owner, their pets, and all tasks to a JSON file.

    Enums are stored as their string name/value so the file is human-readable.
    Overwrites the file on every call — call after any state change to keep
    the saved data in sync.
    """
    payload = _owner_schema.dump(owner)
    # dump() returns plain dicts; enums need manual conversion for readability
    for pet_dict in payload.get("pets", []):
        for task_dict in pet_dict.get("tasks", []):
            task_dict["priority"]  = task_dict["priority"]   # already a str from dump
            task_dict["frequency"] = task_dict["frequency"]  # already a str from dump

    Path(path).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def load_from_json(path: str | Path = "data.json") -> Owner:
    """Deserialize an Owner (with pets and tasks) from a JSON file.

    Raises FileNotFoundError if the file does not exist — callers should
    handle this to gracefully start a fresh session when no save file is present.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return _owner_schema.load(raw)
