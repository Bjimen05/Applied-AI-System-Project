"""Specialized task-urgency model for PawPal+.

Not a hosted or trained model — a structured-prompting-style classifier:
a fixed set of input features always produces the same output schema
(TaskAssessment), the offline equivalent of asking an LLM to return JSON
with a locked-down shape. It replaces a single fixed "boost within 60
minutes" rule with a continuous score blending declared priority, deadline
pressure, overdue status, and RAG-flagged health relevance — so ordering
decisions can differ from the Scheduler's own tie-break logic and the
Evaluator can catch cases the raw Priority enum misses.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from pawpal_system import Pet, Priority, Task
from retriever import RISK_CATEGORIES, Retriever


class UrgencyTier(Enum):
    ROUTINE = "routine"
    SOON = "soon"
    URGENT = "urgent"
    CRITICAL = "critical"


_TIER_THRESHOLDS = [
    (85.0, UrgencyTier.CRITICAL),
    (65.0, UrgencyTier.URGENT),
    (40.0, UrgencyTier.SOON),
]

_PRIORITY_BASE = {Priority.HIGH: 70.0, Priority.MEDIUM: 45.0, Priority.LOW: 20.0}

_OVERDUE_BONUS = 25.0
_RISK_BONUS = 15.0
_RISK_THRESHOLD = 0.12


@dataclass
class TaskAssessment:
    task_title: str
    urgency_tier: UrgencyTier
    urgency_score: float
    rationale: str


class TaskClassifier:
    """Structured-output urgency classifier — same schema every call."""

    def __init__(self, retriever: Retriever | None = None, today: date | None = None) -> None:
        self.retriever = retriever if retriever is not None else Retriever()
        self.today = today or date.today()

    def classify(self, task: Task, pet: Pet, day_start: int) -> TaskAssessment:
        base = _PRIORITY_BASE[task.priority]

        minutes_until_due = max(task.due_time - day_start, 0)
        time_pressure = max(0.0, 30.0 - minutes_until_due / 12.0)

        overdue = (not task.completed) and task.due_date < self.today
        overdue_bonus = _OVERDUE_BONUS if overdue else 0.0

        risk_hits = self.retriever.retrieve_for_task(task.title, task.description, pet.species, top_k=1)
        is_risky = bool(
            risk_hits
            and risk_hits[0].document.category in RISK_CATEGORIES
            and risk_hits[0].score >= _RISK_THRESHOLD
        )
        risk_bonus = _RISK_BONUS if is_risky else 0.0

        score = min(100.0, base + time_pressure + overdue_bonus + risk_bonus)

        tier = UrgencyTier.ROUTINE
        for threshold, candidate in _TIER_THRESHOLDS:
            if score >= threshold:
                tier = candidate
                break

        clauses = [f"{task.priority.name} declared priority ({base:.0f} base pts)"]
        if time_pressure > 0:
            clauses.append(f"due in {minutes_until_due} min (+{time_pressure:.0f} pts)")
        if overdue:
            clauses.append(f"overdue since {task.due_date} (+{overdue_bonus:.0f} pts)")
        if risk_bonus:
            clauses.append(f"care-guide flags this as health-related (+{risk_bonus:.0f} pts)")
        rationale = f"{tier.value.upper()} ({score:.0f}/100): " + "; ".join(clauses)

        return TaskAssessment(task.title, tier, score, rationale)
