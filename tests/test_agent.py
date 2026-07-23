from datetime import date, timedelta

from pawpal_system import Owner, Pet, Priority, Task
from retriever import Document, Retriever
from agent import PawPalAgent


def test_agent_promotes_overdue_task_and_reschedules_it_ahead(tmp_path):
    """A MEDIUM, overdue task that the model ranks CRITICAL should get
    promoted to HIGH by the agent and bump out a HIGH task that has no
    time pressure — a real change in which task ends up scheduled, not
    just a reported warning."""
    owner = Owner(name="Test", available_minutes=15, day_start=480)
    pet = Pet(name="Buddy", species="dog", breed="Mixed", age=3)
    owner.add_pet(pet)

    task_a = Task(title="Walk", description="", duration_minutes=15,
                  priority=Priority.HIGH, due_time=700)
    task_b = Task(title="Grooming", description="", duration_minutes=15,
                  priority=Priority.MEDIUM, due_time=650)
    task_b.due_date = date.today() - timedelta(days=1)

    pet.add_task(task_a)
    pet.add_task(task_b)

    agent = PawPalAgent(owner, retriever=Retriever([]))
    result = agent.run(save_path=str(tmp_path / "data.json"))

    scheduled_titles = {e.task.title for e in result.plan.entries}
    assert scheduled_titles == {"Grooming"}
    assert task_b.priority == Priority.HIGH
    assert any("promoted" in a.lower() for a in result.actions_taken)
    assert result.saved is True
    assert (tmp_path / "data.json").exists()


def test_agent_leaves_plan_unchanged_when_no_mismatch(tmp_path):
    owner = Owner(name="Test", available_minutes=60, day_start=480)
    pet = Pet(name="Buddy", species="dog", breed="Mixed", age=3)
    owner.add_pet(pet)
    task = Task(title="Feeding", description="", duration_minutes=10,
                priority=Priority.HIGH, due_time=500)
    pet.add_task(task)

    agent = PawPalAgent(owner, retriever=Retriever([]))
    result = agent.run(save_path=str(tmp_path / "data.json"))

    assert len(result.plan.entries) == 1
    assert result.plan.entries[0].task.title == "Feeding"
    assert not any("promoted" in a.lower() for a in result.actions_taken)
    assert result.saved is True


def test_agent_blocks_save_for_high_risk_task_until_human_reviewed(tmp_path):
    owner = Owner(name="Test", available_minutes=60, day_start=480)
    pet = Pet(name="Buddy", species="dog", breed="Mixed", age=3)
    owner.add_pet(pet)
    risky_doc = Document("test-med", "any", "medication", "give the prescribed insulin dose on schedule")
    task = Task(title="Insulin Shot", description="prescribed insulin dose", duration_minutes=10,
                priority=Priority.HIGH, due_time=500)
    pet.add_task(task)

    save_path = str(tmp_path / "data.json")
    agent = PawPalAgent(owner, retriever=Retriever([risky_doc]))

    unreviewed = agent.run(human_reviewed=False, save_path=save_path)
    assert unreviewed.saved is False
    assert unreviewed.needs_human_review is True
    assert not (tmp_path / "data.json").exists()

    reviewed = agent.run(human_reviewed=True, save_path=save_path)
    assert reviewed.saved is True
    assert (tmp_path / "data.json").exists()


def test_agent_result_includes_care_tips_and_assessments(tmp_path):
    owner = Owner(name="Test", available_minutes=60, day_start=480)
    pet = Pet(name="Buddy", species="rabbit", breed="Mixed", age=2)
    owner.add_pet(pet)
    task = Task(title="Enrichment", description="tunnels and chew toys", duration_minutes=20,
                priority=Priority.LOW, due_time=900)
    pet.add_task(task)

    agent = PawPalAgent(owner)
    result = agent.run(save_path=str(tmp_path / "data.json"))

    assert "Enrichment" in result.assessments
    assert "Enrichment" in result.care_tips
