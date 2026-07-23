from datetime import date, timedelta

import pytest

from pawpal_system import (
    DailyPlan, Frequency, Owner, Pet, Priority, ScheduledEntry, Scheduler,
    SKIP_BUDGET, SKIP_DEADLINE, Task,
)
from evaluator import Evaluator, Severity, safe_save_plan
import evaluator as evaluator_module
from retriever import Document, Retriever


def make_owner(available_minutes=120, day_start=480):
    return Owner(name="Jordan", available_minutes=available_minutes, day_start=day_start)


def make_task(title, duration, priority, due_time, description="", frequency=Frequency.ONCE):
    return Task(
        title=title, description=description, duration_minutes=duration,
        priority=priority, due_time=due_time, frequency=frequency,
    )


# ---------------------------------------------------------------------------
# Clean plan — no findings
# ---------------------------------------------------------------------------

def test_clean_plan_has_no_findings():
    owner = make_owner()
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    task = make_task("Morning Walk", 30, Priority.HIGH, due_time=540)
    pet.add_task(task)
    owner.add_pet(pet)

    plan = Scheduler(owner).generate_plan()
    findings = Evaluator(plan).run()

    assert findings == []
    assert Evaluator.passed(findings)
    assert not Evaluator.requires_human_review(findings)


# ---------------------------------------------------------------------------
# Integrity checks
# ---------------------------------------------------------------------------

def test_duration_mismatch_is_critical():
    owner = make_owner()
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    task = make_task("Feeding", 10, Priority.HIGH, due_time=600)
    entry = ScheduledEntry(pet=pet, task=task, start_time=480, end_time=500)  # 20 min, not 10
    plan = DailyPlan(owner=owner, date=str(date.today()), entries=[entry], skipped_tasks=[])

    findings = Evaluator(plan).run()

    assert any(f.code == "duration_mismatch" and f.severity == Severity.CRITICAL for f in findings)
    assert not Evaluator.passed(findings)


def test_deadline_violation_is_critical():
    owner = make_owner()
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    task = make_task("Feeding", 10, Priority.HIGH, due_time=485)
    entry = ScheduledEntry(pet=pet, task=task, start_time=480, end_time=490)  # finishes after due_time
    plan = DailyPlan(owner=owner, date=str(date.today()), entries=[entry], skipped_tasks=[])

    findings = Evaluator(plan).run()

    assert any(f.code == "deadline_violated" for f in findings)
    assert not Evaluator.passed(findings)


def test_overlapping_entries_is_critical():
    owner = make_owner()
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    t1 = make_task("Walk", 30, Priority.HIGH, due_time=600)
    t2 = make_task("Feeding", 10, Priority.HIGH, due_time=600)
    e1 = ScheduledEntry(pet=pet, task=t1, start_time=480, end_time=510)
    e2 = ScheduledEntry(pet=pet, task=t2, start_time=500, end_time=510)  # overlaps e1
    plan = DailyPlan(owner=owner, date=str(date.today()), entries=[e1, e2], skipped_tasks=[])

    findings = Evaluator(plan).run()

    assert any(f.code == "overlapping_entries" for f in findings)


# ---------------------------------------------------------------------------
# Budget check
# ---------------------------------------------------------------------------

def test_budget_exceeded_is_critical():
    owner = make_owner(available_minutes=20)
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    task = make_task("Walk", 30, Priority.HIGH, due_time=600)
    entry = ScheduledEntry(pet=pet, task=task, start_time=480, end_time=510)
    plan = DailyPlan(owner=owner, date=str(date.today()), entries=[entry], skipped_tasks=[])

    findings = Evaluator(plan).run()

    assert any(f.code == "budget_exceeded" for f in findings)
    assert not Evaluator.passed(findings)


# ---------------------------------------------------------------------------
# Priority inversion
# ---------------------------------------------------------------------------

def test_priority_inversion_flagged_as_warning():
    owner = make_owner()
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    low = make_task("Enrichment", 20, Priority.LOW, due_time=700)
    high = make_task("Meds Reminder Walk", 30, Priority.HIGH, due_time=485)  # impossible deadline

    scheduled_entry = ScheduledEntry(pet=pet, task=low, start_time=480, end_time=500)
    plan = DailyPlan(
        owner=owner, date=str(date.today()),
        entries=[scheduled_entry],
        skipped_tasks=[(pet, high, SKIP_DEADLINE)],
    )

    findings = Evaluator(plan).run()

    assert any(f.code == "priority_inversion" and f.severity == Severity.WARNING for f in findings)
    assert Evaluator.passed(findings)  # WARNING, not CRITICAL


# ---------------------------------------------------------------------------
# High-risk task flag → requires human review
# ---------------------------------------------------------------------------

def test_high_risk_scheduled_task_requires_review():
    owner = make_owner()
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    task = make_task("Vet Check", 30, Priority.HIGH, due_time=600)
    entry = ScheduledEntry(pet=pet, task=task, start_time=480, end_time=510)
    plan = DailyPlan(owner=owner, date=str(date.today()), entries=[entry], skipped_tasks=[])

    findings = Evaluator(plan).run()

    assert any(f.code == "high_risk_task" and f.requires_human_review for f in findings)
    assert Evaluator.passed(findings)
    assert Evaluator.requires_human_review(findings)


def test_high_risk_grounded_by_retrieval_without_keyword_match(monkeypatch):
    """A task with no HIGH_RISK_KEYWORDS hit should still be flagged when the
    RAG layer finds a matching medication/vet care-guide passage."""
    custom_doc = Document(
        "test-med-1", "any", "medication",
        "Ear drops must be given on a strict schedule after a recent visit",
    )
    monkeypatch.setattr(evaluator_module, "_retriever", Retriever([custom_doc]))

    owner = make_owner()
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    task = make_task(
        "Ear Drops", 5, Priority.MEDIUM, due_time=600,
        description="twice daily as directed by the clinic",
    )
    entry = ScheduledEntry(pet=pet, task=task, start_time=480, end_time=485)
    plan = DailyPlan(owner=owner, date=str(date.today()), entries=[entry], skipped_tasks=[])

    findings = Evaluator(plan).run()

    assert any(
        f.code == "high_risk_task" and f.requires_human_review and "Care-guide match" in f.message
        for f in findings
    )


def test_no_risk_when_neither_keyword_nor_retrieval_match(monkeypatch):
    monkeypatch.setattr(evaluator_module, "_retriever", Retriever([]))

    owner = make_owner()
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    task = make_task("Morning Walk", 30, Priority.HIGH, due_time=540)
    entry = ScheduledEntry(pet=pet, task=task, start_time=480, end_time=510)
    plan = DailyPlan(owner=owner, date=str(date.today()), entries=[entry], skipped_tasks=[])

    findings = Evaluator(plan).run()

    assert not any(f.code in ("high_risk_task", "high_risk_task_skipped") for f in findings)


def test_high_risk_skipped_task_requires_review():
    owner = make_owner()
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    task = make_task("Insulin dose", 10, Priority.HIGH, due_time=485)
    plan = DailyPlan(
        owner=owner, date=str(date.today()), entries=[],
        skipped_tasks=[(pet, task, SKIP_DEADLINE)],
    )

    findings = Evaluator(plan).run()

    assert any(f.code == "high_risk_task_skipped" and f.requires_human_review for f in findings)


# ---------------------------------------------------------------------------
# Overdue tasks
# ---------------------------------------------------------------------------

def test_overdue_pending_task_flagged():
    owner = make_owner()
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    stale_task = make_task("Grooming", 15, Priority.MEDIUM, due_time=600)
    stale_task.due_date = date.today() - timedelta(days=3)
    pet.add_task(stale_task)
    owner.add_pet(pet)

    plan = DailyPlan(owner=owner, date=str(date.today()), entries=[], skipped_tasks=[])
    findings = Evaluator(plan).run()

    assert any(f.code == "overdue_task" for f in findings)


# ---------------------------------------------------------------------------
# safe_save_plan gating — the behavior-changing integration point
# ---------------------------------------------------------------------------

def test_safe_save_plan_blocks_on_critical(tmp_path):
    owner = make_owner(available_minutes=20)
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    task = make_task("Walk", 30, Priority.HIGH, due_time=600)
    entry = ScheduledEntry(pet=pet, task=task, start_time=480, end_time=510)
    plan = DailyPlan(owner=owner, date=str(date.today()), entries=[entry], skipped_tasks=[])

    path = tmp_path / "data.json"
    saved, findings = safe_save_plan(owner, plan, path=path, human_reviewed=True)

    assert saved is False
    assert not path.exists()


def test_safe_save_plan_blocks_high_risk_without_review(tmp_path):
    owner = make_owner()
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    task = make_task("Vet Check", 30, Priority.HIGH, due_time=600)
    entry = ScheduledEntry(pet=pet, task=task, start_time=480, end_time=510)
    plan = DailyPlan(owner=owner, date=str(date.today()), entries=[entry], skipped_tasks=[])

    path = tmp_path / "data.json"
    saved, findings = safe_save_plan(owner, plan, path=path, human_reviewed=False)

    assert saved is False
    assert not path.exists()


def test_safe_save_plan_succeeds_after_human_review(tmp_path):
    owner = make_owner()
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    task = make_task("Vet Check", 30, Priority.HIGH, due_time=600)
    entry = ScheduledEntry(pet=pet, task=task, start_time=480, end_time=510)
    plan = DailyPlan(owner=owner, date=str(date.today()), entries=[entry], skipped_tasks=[])

    path = tmp_path / "data.json"
    saved, findings = safe_save_plan(owner, plan, path=path, human_reviewed=True)

    assert saved is True
    assert path.exists()


def test_safe_save_plan_succeeds_for_clean_plan(tmp_path):
    owner = make_owner()
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    task = make_task("Morning Walk", 30, Priority.HIGH, due_time=540)
    pet.add_task(task)
    owner.add_pet(pet)
    plan = Scheduler(owner).generate_plan()

    path = tmp_path / "data.json"
    saved, findings = safe_save_plan(owner, plan, path=path)

    assert saved is True
    assert path.exists()
