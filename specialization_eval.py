"""Stretch: Fine-Tuning/Specialization demonstration.

A naive BASELINE maps declared Priority directly to an urgency label and
ignores everything else the specialized TaskClassifier considers --
deadline pressure, overdue status, RAG-flagged risk. This script runs
both against the same synthetic task set and prints where they agree and
where they measurably differ. Results are documented in model_card.md
under "Specialized Model vs. Baseline".

Run: `python specialization_eval.py`
"""
from __future__ import annotations

import sys
from datetime import date, timedelta

from tabulate import tabulate

from pawpal_system import Pet, Priority, Task
from specialized_model import TaskClassifier

_BASELINE_TIER = {
    Priority.HIGH: "critical",
    Priority.MEDIUM: "soon",
    Priority.LOW: "routine",
}

# (title, description, priority, due_time, due_date_offset_days)
SYNTHETIC_TASKS = [
    ("Feeding", "", Priority.HIGH, 490, 0),
    ("Grooming (overdue)", "", Priority.MEDIUM, 700, -3),
    ("Enrichment", "", Priority.LOW, 1200, 0),
    ("Afternoon walk", "", Priority.MEDIUM, 560, 0),
    ("Evening walk", "", Priority.HIGH, 1200, 0),
    ("Vet Check", "Annual checkup", Priority.MEDIUM, 650, 0),
    ("Litter box (overdue)", "", Priority.LOW, 700, -2),
    ("Insulin dose", "prescribed insulin dose schedule", Priority.HIGH, 500, 0),
    ("Brushing", "", Priority.MEDIUM, 560, 0),
    ("Nail trim", "", Priority.LOW, 560, 0),
]

DAY_START = 480


def run_baseline_comparison():
    classifier = TaskClassifier()
    pet = Pet(name="Demo", species="dog", breed="Mixed", age=3)
    rows = []
    agree = 0
    for title, desc, priority, due_time, offset in SYNTHETIC_TASKS:
        task = Task(title=title, description=desc, duration_minutes=10,
                    priority=priority, due_time=due_time)
        task.due_date = date.today() + timedelta(days=offset)
        assessment = classifier.classify(task, pet, DAY_START)
        baseline = _BASELINE_TIER[priority]
        specialized = assessment.urgency_tier.value
        matches = baseline == specialized
        agree += matches
        rows.append([
            title, priority.name, baseline, specialized,
            f"{assessment.urgency_score:.0f}/100", "match" if matches else "DIFFERS",
        ])
    print(tabulate(
        rows, headers=["Task", "Priority", "Baseline", "Specialized", "Score", "Agreement"],
        tablefmt="rounded_outline",
    ))
    total = len(SYNTHETIC_TASKS)
    print(f"\nAgreement: {agree}/{total} ({agree / total:.0%})")
    print(
        "Disagreements are the specialized model correcting the baseline's blind spots: "
        "it recognizes a HIGH task with hours of slack isn't truly critical, and that an "
        "overdue or soon-due LOW/MEDIUM task deserves more urgency than a static priority label gives it."
    )
    return agree, total


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    run_baseline_comparison()
