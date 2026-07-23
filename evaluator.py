"""Reliability layer for PawPal+: guardrail checks that gate schedule persistence.

The Evaluator inspects a generated DailyPlan for integrity violations, unfair
scheduling, and high-risk tasks (medication/vet care) before the plan is
allowed to be saved. This is not a passive report — `safe_save_plan` is the
only sanctioned way to persist a plan, and it refuses to write to disk when
a CRITICAL finding is present or a high-risk task hasn't been explicitly
reviewed by a human.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path

from pawpal_system import DailyPlan, Owner, Priority, SKIP_DEADLINE, save_to_json
from retriever import RISK_CATEGORIES, Retriever
from specialized_model import TaskClassifier, UrgencyTier

HIGH_RISK_KEYWORDS = {
    "med", "meds", "medication", "medicine", "insulin", "dosage", "dose",
    "vet", "surgery", "injury", "injured", "allergy", "allergic", "emergency",
}

# Retrieval grounding threshold: minimum Jaccard overlap between a task's
# title/description and a care-guide passage before it counts as evidence.
GROUNDING_THRESHOLD = 0.12

_retriever = Retriever()


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Finding:
    code: str
    severity: Severity
    message: str
    requires_human_review: bool = False


def _is_high_risk(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in HIGH_RISK_KEYWORDS)


def _retrieval_risk_evidence(title: str, description: str, species: str) -> str | None:
    """Return a grounding passage's text if RAG surfaces a medication/vet care
    guide relevant to this task, even when no fixed keyword matched."""
    hits = _retriever.retrieve_for_task(title, description, species, top_k=1)
    for hit in hits:
        if hit.document.category in RISK_CATEGORIES and hit.score >= GROUNDING_THRESHOLD:
            return hit.document.text
    return None


class Evaluator:
    """Runs guardrail checks against a DailyPlan."""

    def __init__(self, plan: DailyPlan, today: date | None = None) -> None:
        self.plan = plan
        self.today = today or date.today()

    def run(self) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(self._check_integrity())
        findings.extend(self._check_budget())
        findings.extend(self._check_priority_inversion())
        findings.extend(self._check_high_risk())
        findings.extend(self._check_overdue())
        findings.extend(self._check_model_priority_mismatch())
        return findings

    def _check_integrity(self) -> list[Finding]:
        findings = []
        for e in self.plan.entries:
            if e.end_time - e.start_time != e.task.duration_minutes:
                findings.append(Finding(
                    "duration_mismatch", Severity.CRITICAL,
                    f"'{e.task.title}' ({e.pet.name}) scheduled duration does not match "
                    f"task.duration_minutes — possible scheduler bug.",
                ))
            if e.end_time > e.task.due_time:
                findings.append(Finding(
                    "deadline_violated", Severity.CRITICAL,
                    f"'{e.task.title}' ({e.pet.name}) is scheduled to finish at "
                    f"{e.end_time} but is due by {e.task.due_time}.",
                ))

        sorted_entries = sorted(self.plan.entries, key=lambda e: e.start_time)
        for prev, curr in zip(sorted_entries, sorted_entries[1:]):
            if curr.start_time < prev.end_time:
                findings.append(Finding(
                    "overlapping_entries", Severity.CRITICAL,
                    f"'{prev.task.title}' ({prev.pet.name}) overlaps with "
                    f"'{curr.task.title}' ({curr.pet.name}) in the generated plan.",
                ))
        return findings

    def _check_budget(self) -> list[Finding]:
        used = self.plan.total_time_used()
        budget = self.plan.owner.available_minutes
        if used > budget:
            return [Finding(
                "budget_exceeded", Severity.CRITICAL,
                f"Plan uses {used} minutes but only {budget} are available.",
            )]
        return []

    def _check_priority_inversion(self) -> list[Finding]:
        findings = []
        skipped_high = [
            (pet, task) for pet, task, reason in self.plan.skipped_tasks
            if task.priority == Priority.HIGH and reason == SKIP_DEADLINE
        ]
        for pet, task in skipped_high:
            worse_scheduled = [
                e for e in self.plan.entries
                if e.task.priority_rank() > task.priority_rank()
            ]
            if worse_scheduled:
                findings.append(Finding(
                    "priority_inversion", Severity.WARNING,
                    f"HIGH priority task '{task.title}' ({pet.name}) was skipped while "
                    f"lower-priority task(s) were scheduled ahead of it.",
                ))
        return findings

    def _check_model_priority_mismatch(self) -> list[Finding]:
        """Use the specialized TaskClassifier's continuous urgency score to
        catch skips the raw Priority enum can't see — e.g. a MEDIUM task
        that's overdue and health-related but got skipped for budget reasons
        while a plain HIGH task was scheduled instead."""
        classifier = TaskClassifier(retriever=_retriever, today=self.today)
        findings = []
        owner = self.plan.owner

        scheduled_scores = [
            classifier.classify(e.task, e.pet, owner.day_start).urgency_score
            for e in self.plan.entries
        ]
        max_scheduled = max(scheduled_scores, default=0.0)

        for pet, task, _reason in self.plan.skipped_tasks:
            assessment = classifier.classify(task, pet, owner.day_start)
            if assessment.urgency_tier not in (UrgencyTier.URGENT, UrgencyTier.CRITICAL):
                continue
            if assessment.urgency_score <= max_scheduled:
                continue
            findings.append(Finding(
                "model_priority_mismatch", Severity.WARNING,
                f"Specialized model rates '{task.title}' ({pet.name}) as "
                f"{assessment.urgency_tier.value.upper()} ({assessment.urgency_score:.0f}/100) "
                f"but it was skipped while lower-scored tasks were scheduled. {assessment.rationale}",
                requires_human_review=(assessment.urgency_tier == UrgencyTier.CRITICAL),
            ))
        return findings

    def _assess_risk(self, pet, task) -> str | None:
        """Return a Finding message suffix if this task is high-risk, combining
        the fixed keyword list with RAG-grounded evidence from the knowledge
        base. Returns None if neither signal fires."""
        keyword_hit = _is_high_risk(task.title) or _is_high_risk(task.description)
        evidence = _retrieval_risk_evidence(task.title, task.description, pet.species)
        if not keyword_hit and not evidence:
            return None
        if evidence:
            return f' Care-guide match: "{evidence}"'
        return ""

    def _check_high_risk(self) -> list[Finding]:
        findings = []
        seen = set()
        for e in self.plan.entries:
            key = (e.pet.name, e.task.title)
            if key in seen:
                continue
            suffix = self._assess_risk(e.pet, e.task)
            if suffix is not None:
                seen.add(key)
                findings.append(Finding(
                    "high_risk_task", Severity.WARNING,
                    f"'{e.task.title}' ({e.pet.name}) looks health/medication-related "
                    f"and needs owner sign-off before the plan is saved.{suffix}",
                    requires_human_review=True,
                ))
        for pet, task, _reason in self.plan.skipped_tasks:
            key = (pet.name, task.title)
            if key in seen:
                continue
            suffix = self._assess_risk(pet, task)
            if suffix is not None:
                seen.add(key)
                findings.append(Finding(
                    "high_risk_task_skipped", Severity.WARNING,
                    f"'{task.title}' ({pet.name}) is health/medication-related and was "
                    f"SKIPPED — needs owner review before the plan is saved.{suffix}",
                    requires_human_review=True,
                ))
        return findings

    def _check_overdue(self) -> list[Finding]:
        findings = []
        for pet in self.plan.owner.pets:
            for task in pet.get_pending_tasks():
                if task.due_date < self.today:
                    findings.append(Finding(
                        "overdue_task", Severity.WARNING,
                        f"'{task.title}' ({pet.name}) was due {task.due_date} and is still pending.",
                    ))
        return findings

    @staticmethod
    def passed(findings: list[Finding]) -> bool:
        """True if no CRITICAL findings — plan is structurally safe to save."""
        return not any(f.severity == Severity.CRITICAL for f in findings)

    @staticmethod
    def requires_human_review(findings: list[Finding]) -> bool:
        """True if a human must explicitly sign off before this plan is saved."""
        return any(f.requires_human_review for f in findings)


def safe_save_plan(
    owner: Owner,
    plan: DailyPlan,
    path: str | Path = "data.json",
    *,
    human_reviewed: bool = False,
) -> tuple[bool, list[Finding]]:
    """The only sanctioned entry point for persisting a plan's owner state.

    Runs the Evaluator first. Refuses to save (returns False) when:
      - any CRITICAL finding is present, regardless of human_reviewed, or
      - a finding requires human review and human_reviewed is False.

    Returns (saved, findings) so callers can display findings either way.
    """
    findings = Evaluator(plan).run()

    if not Evaluator.passed(findings):
        return False, findings

    if Evaluator.requires_human_review(findings) and not human_reviewed:
        return False, findings

    save_to_json(owner, path)
    return True, findings
