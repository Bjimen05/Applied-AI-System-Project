"""Agentic workflow for PawPal+.

Orchestrates the Scheduler (deterministic core), Retriever (RAG),
TaskClassifier (specialized model), and Evaluator (reliability gate) into
one decision loop, instead of the linear "generate -> evaluate -> display"
sequence called directly from the UI/CLI.

The agent doesn't just report problems — it acts on the ones it can safely
fix: when the Evaluator's model_priority_mismatch check says a skipped task
is more urgent (per the specialized model) than what got scheduled, the
agent promotes that task's declared Priority to HIGH and re-plans, up to
MAX_REPAIR_ATTEMPTS times, before handing the result to the same
human-review save gate used everywhere else. If a CRITICAL finding shows up
(a Scheduler integrity bug), the agent has no automatic fix and stops,
leaving the plan unsaved.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pawpal_system import DailyPlan, Owner, Priority, Scheduler
from evaluator import Evaluator, Finding, safe_save_plan
from retriever import Retriever
from specialized_model import TaskAssessment, TaskClassifier, UrgencyTier

MAX_REPAIR_ATTEMPTS = 2

_PROMOTABLE_TIERS = (UrgencyTier.URGENT, UrgencyTier.CRITICAL)


@dataclass
class AgentResult:
    plan: DailyPlan
    findings: list[Finding]
    actions_taken: list[str]
    saved: bool
    needs_human_review: bool
    care_tips: dict[str, str] = field(default_factory=dict)
    assessments: dict[str, TaskAssessment] = field(default_factory=dict)


class PawPalAgent:
    def __init__(
        self, owner: Owner,
        retriever: Retriever | None = None,
        classifier: TaskClassifier | None = None,
    ) -> None:
        self.owner = owner
        self.retriever = retriever if retriever is not None else Retriever()
        self.classifier = classifier if classifier is not None else TaskClassifier(retriever=self.retriever)

    def run(self, *, human_reviewed: bool = False, save_path: str = "data.json") -> AgentResult:
        actions: list[str] = []
        scheduler = Scheduler(self.owner)
        plan = scheduler.generate_plan()
        actions.append("Generated a candidate plan with the Scheduler.")
        findings = Evaluator(plan).run()

        for attempt in range(1, MAX_REPAIR_ATTEMPTS + 1):
            if not Evaluator.passed(findings):
                actions.append(
                    f"Attempt {attempt}: a CRITICAL issue was found and the agent has no "
                    f"automatic repair for it; stopping without saving."
                )
                break

            promoted = self._promote_mismatched_tasks(plan)
            if not promoted:
                break

            actions.append(
                f"Attempt {attempt}: the model rated {', '.join(promoted)} as more urgent than "
                f"what got scheduled, so the agent promoted it to HIGH priority and re-planned."
            )
            plan = scheduler.generate_plan()
            findings = Evaluator(plan).run()

        care_tips: dict[str, str] = {}
        assessments: dict[str, TaskAssessment] = {}
        for pet, task in scheduler.collect_tasks():
            hits = self.retriever.retrieve_for_task(task.title, task.description, pet.species, top_k=1)
            if hits:
                care_tips[task.title] = hits[0].document.text
            assessments[task.title] = self.classifier.classify(task, pet, self.owner.day_start)

        saved = False
        if Evaluator.passed(findings):
            saved, findings = safe_save_plan(self.owner, plan, path=save_path, human_reviewed=human_reviewed)
            actions.append("Saved the plan." if saved else "Save blocked — pending human review of flagged tasks.")
        else:
            actions.append("Plan still has a CRITICAL issue after repair attempts — not saved.")

        return AgentResult(
            plan=plan, findings=findings, actions_taken=actions, saved=saved,
            needs_human_review=Evaluator.requires_human_review(findings),
            care_tips=care_tips, assessments=assessments,
        )

    def _promote_mismatched_tasks(self, plan: DailyPlan) -> list[str]:
        """Mirrors Evaluator._check_model_priority_mismatch's own logic to find
        skipped tasks the model ranks above what's scheduled, then promotes
        each to HIGH priority so the Scheduler's own ordering favors it on
        the next pass. Returns the titles actually changed."""
        scheduled_scores = [
            self.classifier.classify(e.task, e.pet, self.owner.day_start).urgency_score
            for e in plan.entries
        ]
        max_scheduled = max(scheduled_scores, default=0.0)

        promoted = []
        for pet, task, _reason in plan.skipped_tasks:
            if task.priority == Priority.HIGH:
                continue
            assessment = self.classifier.classify(task, pet, self.owner.day_start)
            if assessment.urgency_tier in _PROMOTABLE_TIERS and assessment.urgency_score > max_scheduled:
                task.priority = Priority.HIGH
                promoted.append(task.title)
        return promoted
