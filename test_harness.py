"""Stretch: Test Harness / Evaluation Script.

Runs the system (Scheduler, Evaluator, PawPalAgent, Retriever) against a
battery of predefined scenarios and prints a PASS/FAIL summary --
independent of, and complementary to, the pytest suite (pytest checks
internals in isolation; this checks observable end-to-end behavior).

Run: `python test_harness.py`
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import date, timedelta

from tabulate import tabulate

from pawpal_system import DailyPlan, Owner, Pet, Priority, ScheduledEntry, Task
from evaluator import safe_save_plan
from retriever import Retriever
from agent import PawPalAgent


def _tmp(name: str) -> str:
    return os.path.join(tempfile.gettempdir(), name)


def check_clean_plan_autosaves() -> bool:
    owner = Owner(name="H1", available_minutes=60, day_start=480)
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    owner.add_pet(pet)
    pet.add_task(Task("Feeding", "", 10, Priority.HIGH, due_time=500))
    result = PawPalAgent(owner).run(save_path=_tmp("harness_clean.json"))
    return result.saved and not result.findings


def check_risky_task_blocks_then_saves() -> bool:
    owner = Owner(name="H2", available_minutes=60, day_start=480)
    pet = Pet(name="Buddy", species="dog", breed="Mixed", age=3)
    owner.add_pet(pet)
    pet.add_task(Task("Vet Check", "Annual checkup", 30, Priority.HIGH, due_time=570))
    agent = PawPalAgent(owner)
    path = _tmp("harness_risky.json")
    unreviewed = agent.run(human_reviewed=False, save_path=path)
    reviewed = agent.run(human_reviewed=True, save_path=path)
    return (not unreviewed.saved) and reviewed.saved


def check_budget_exceeded_blocks_save() -> bool:
    owner = Owner(name="H3", available_minutes=20, day_start=480)
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    task = Task("Walk", "", 30, Priority.HIGH, due_time=600)
    entry = ScheduledEntry(pet=pet, task=task, start_time=480, end_time=510)
    plan = DailyPlan(owner=owner, date=str(date.today()), entries=[entry], skipped_tasks=[])
    saved, findings = safe_save_plan(owner, plan, path=_tmp("harness_budget.json"))
    return (not saved) and any(f.severity.value == "critical" for f in findings)


def check_priority_mismatch_repair_reschedules() -> bool:
    owner = Owner(name="H4", available_minutes=15, day_start=480)
    pet = Pet(name="Max", species="dog", breed="Mixed", age=4)
    owner.add_pet(pet)
    walk = Task("Walk", "", 15, Priority.HIGH, due_time=700)
    groom = Task("Grooming", "", 15, Priority.MEDIUM, due_time=650)
    groom.due_date = date.today() - timedelta(days=1)
    pet.add_task(walk)
    pet.add_task(groom)
    result = PawPalAgent(owner, retriever=Retriever([])).run(
        human_reviewed=True, save_path=_tmp("harness_repair.json"),
    )
    scheduled = {e.task.title for e in result.plan.entries}
    return scheduled == {"Grooming"}


def check_retrieval_grounds_care_tip() -> bool:
    owner = Owner(name="H5", available_minutes=60, day_start=480)
    pet = Pet(name="Rex", species="dog", breed="Golden Retriever", age=2)
    owner.add_pet(pet)
    pet.add_task(Task("Morning Walk", "walk around the block", 30, Priority.HIGH, due_time=520))
    result = PawPalAgent(owner).run(save_path=_tmp("harness_rag.json"))
    return "Morning Walk" in result.care_tips


SCENARIOS = [
    ("Clean plan auto-saves with no findings", check_clean_plan_autosaves),
    ("Risky task blocks then saves after human review", check_risky_task_blocks_then_saves),
    ("Manually-built over-budget plan blocks on CRITICAL", check_budget_exceeded_blocks_save),
    ("Agent repair loop reschedules the higher-urgency task", check_priority_mismatch_repair_reschedules),
    ("Retrieval grounds a care tip for a scheduled task", check_retrieval_grounds_care_tip),
]


def run_scenarios():
    rows = []
    passed = 0
    for name, check in SCENARIOS:
        try:
            ok = check()
        except Exception as exc:
            ok = False
            name = f"{name} (error: {exc})"
        rows.append([name, "PASS" if ok else "FAIL"])
        passed += int(ok)
    print(tabulate(rows, headers=["Scenario", "Result"], tablefmt="rounded_outline"))
    total = len(SCENARIOS)
    print(f"\n{passed}/{total} scenarios passed.")
    return passed, total


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    run_scenarios()
