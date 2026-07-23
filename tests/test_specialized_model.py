from datetime import date

from pawpal_system import Frequency, Pet, Priority, Task
from retriever import Document, Retriever
from specialized_model import TaskAssessment, TaskClassifier, UrgencyTier


def make_task(title, duration, priority, due_time, description="", due_date=None):
    return Task(
        title=title, description=description, duration_minutes=duration,
        priority=priority, due_time=due_time, frequency=Frequency.ONCE,
        due_date=due_date or date.today(),
    )


def test_high_priority_due_soon_scores_higher_than_low_priority_far_out():
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    classifier = TaskClassifier(retriever=Retriever([]))

    urgent = make_task("Feeding", 10, Priority.HIGH, due_time=490)
    routine = make_task("Enrichment", 20, Priority.LOW, due_time=1200)

    a_urgent = classifier.classify(urgent, pet, day_start=480)
    a_routine = classifier.classify(routine, pet, day_start=480)

    assert a_urgent.urgency_score > a_routine.urgency_score
    assert a_routine.urgency_tier == UrgencyTier.ROUTINE


def test_overdue_task_scores_higher_than_identical_task_not_overdue():
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    classifier = TaskClassifier(retriever=Retriever([]), today=date(2026, 7, 23))

    fresh = make_task("Grooming", 15, Priority.MEDIUM, due_time=700, due_date=date(2026, 7, 23))
    overdue = make_task("Grooming", 15, Priority.MEDIUM, due_time=700, due_date=date(2026, 7, 20))

    a_fresh = classifier.classify(fresh, pet, day_start=480)
    a_overdue = classifier.classify(overdue, pet, day_start=480)

    assert a_overdue.urgency_score > a_fresh.urgency_score
    assert "overdue" in a_overdue.rationale.lower()


def test_retrieval_flagged_risk_task_scores_higher_than_plain_task():
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    risky_doc = Document("test-risk", "any", "medication", "insulin dose schedule must be followed exactly")
    classifier = TaskClassifier(retriever=Retriever([risky_doc]))

    risky_task = make_task("Insulin Shot", 5, Priority.MEDIUM, due_time=900, description="insulin dose schedule")
    plain_task = make_task("Play Time", 5, Priority.MEDIUM, due_time=900, description="toys and games")

    a_risky = classifier.classify(risky_task, pet, day_start=480)
    a_plain = classifier.classify(plain_task, pet, day_start=480)

    assert a_risky.urgency_score > a_plain.urgency_score
    assert "health-related" in a_risky.rationale.lower()


def test_score_is_clamped_to_100():
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    classifier = TaskClassifier(retriever=Retriever([]), today=date(2026, 7, 23))

    extreme = make_task("Feeding", 10, Priority.HIGH, due_time=480, due_date=date(2026, 7, 1))
    assessment = classifier.classify(extreme, pet, day_start=480)

    assert assessment.urgency_score <= 100.0
    assert assessment.urgency_tier == UrgencyTier.CRITICAL


def test_assessment_has_expected_structured_fields():
    pet = Pet(name="Biscuit", species="dog", breed="Mixed", age=3)
    classifier = TaskClassifier(retriever=Retriever([]))
    task = make_task("Feeding", 10, Priority.LOW, due_time=1300)

    assessment = classifier.classify(task, pet, day_start=480)

    assert isinstance(assessment, TaskAssessment)
    assert assessment.task_title == "Feeding"
    assert isinstance(assessment.urgency_score, float)
    assert isinstance(assessment.rationale, str) and assessment.rationale
