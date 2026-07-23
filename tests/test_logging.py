import logging

from pawpal_system import DailyPlan, Owner, Pet, Priority, ScheduledEntry, Task
from evaluator import Evaluator, safe_save_plan


def make_owner(available_minutes=120, day_start=480):
    return Owner(name="Jordan", available_minutes=available_minutes, day_start=day_start)


def test_evaluator_logs_critical_finding(caplog):
    owner = make_owner(available_minutes=20)
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    task = Task(title="Walk", description="", duration_minutes=30,
                priority=Priority.HIGH, due_time=600)
    entry = ScheduledEntry(pet=pet, task=task, start_time=480, end_time=510)
    plan = DailyPlan(owner=owner, date="2026-01-01", entries=[entry], skipped_tasks=[])

    with caplog.at_level(logging.ERROR, logger="evaluator"):
        Evaluator(plan).run()

    assert any("budget_exceeded" in r.message for r in caplog.records)
    assert all(r.levelno == logging.ERROR for r in caplog.records if "budget_exceeded" in r.message)


def test_evaluator_logs_clean_pass(caplog):
    owner = make_owner()
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    task = Task(title="Feeding", description="", duration_minutes=10,
                priority=Priority.HIGH, due_time=540)
    entry = ScheduledEntry(pet=pet, task=task, start_time=480, end_time=490)
    plan = DailyPlan(owner=owner, date="2026-01-01", entries=[entry], skipped_tasks=[])

    with caplog.at_level(logging.INFO, logger="evaluator"):
        Evaluator(plan).run()

    assert any("passed with no findings" in r.message for r in caplog.records)


def test_safe_save_plan_logs_blocked_save(tmp_path, caplog):
    owner = make_owner(available_minutes=20)
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    task = Task(title="Walk", description="", duration_minutes=30,
                priority=Priority.HIGH, due_time=600)
    entry = ScheduledEntry(pet=pet, task=task, start_time=480, end_time=510)
    plan = DailyPlan(owner=owner, date="2026-01-01", entries=[entry], skipped_tasks=[])

    with caplog.at_level(logging.ERROR, logger="evaluator"):
        safe_save_plan(owner, plan, path=tmp_path / "data.json")

    assert any("Save BLOCKED" in r.message for r in caplog.records)


def test_agent_logs_run_lifecycle(tmp_path, caplog):
    from agent import PawPalAgent
    from retriever import Retriever

    owner = make_owner()
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    task = Task(title="Feeding", description="", duration_minutes=10,
                priority=Priority.HIGH, due_time=540)
    pet.add_task(task)
    owner.add_pet(pet)

    with caplog.at_level(logging.INFO, logger="agent"):
        PawPalAgent(owner, retriever=Retriever([])).run(save_path=str(tmp_path / "data.json"))

    assert any("Agent run started" in r.message for r in caplog.records)
    assert any("Agent run finished" in r.message for r in caplog.records)
