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

import logging
from dataclasses import dataclass, field

from pawpal_system import DailyPlan, Owner, Priority, Scheduler
from evaluator import Evaluator, Finding, safe_save_plan
from retriever import Retriever
from specialized_model import TaskAssessment, TaskClassifier, UrgencyTier

logger = logging.getLogger(__name__)

MAX_REPAIR_ATTEMPTS = 2

_PROMOTABLE_TIERS = (UrgencyTier.URGENT, UrgencyTier.CRITICAL)


@dataclass
class TraceStep:
    """One tool call in the agent's reasoning chain — a machine-parseable
    complement to the human-readable `actions_taken` strings, meant to be
    logged/committed as evidence of the multi-step decision process."""
    step: int
    tool: str
    input_summary: str
    output_summary: str
    decision: str


@dataclass
class AgentResult:
    plan: DailyPlan
    findings: list[Finding]
    actions_taken: list[str]
    saved: bool
    needs_human_review: bool
    care_tips: dict[str, str] = field(default_factory=dict)
    assessments: dict[str, TaskAssessment] = field(default_factory=dict)
    trace: list[TraceStep] = field(default_factory=list)


def trace_to_markdown(trace: list[TraceStep]) -> str:
    """Render a reasoning trace as a markdown table for ai_interactions.md."""
    lines = ["| Step | Tool Called | Input | Output | Decision |", "|---|---|---|---|---|"]
    for t in trace:
        lines.append(f"| {t.step} | `{t.tool}` | {t.input_summary} | {t.output_summary} | {t.decision} |")
    return "\n".join(lines)


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
        trace: list[TraceStep] = []
        step = 0
        logger.info("Agent run started for owner '%s'.", self.owner.name)

        scheduler = Scheduler(self.owner)
        pending_count = len(scheduler.collect_tasks())
        plan = scheduler.generate_plan()
        actions.append("Generated a candidate plan with the Scheduler.")
        step += 1
        trace.append(TraceStep(
            step, "Scheduler.generate_plan",
            f"{pending_count} pending task(s) for '{self.owner.name}'",
            f"{len(plan.entries)} scheduled, {len(plan.skipped_tasks)} skipped",
            "Plan built — proceed to Evaluator.",
        ))

        findings = Evaluator(plan).run()
        step += 1
        n_crit = sum(1 for f in findings if f.severity.value == "critical")
        n_warn = sum(1 for f in findings if f.severity.value == "warning")
        trace.append(TraceStep(
            step, "Evaluator.run",
            f"plan with {len(plan.entries)} entries",
            f"{len(findings)} finding(s) ({n_crit} critical, {n_warn} warning)",
            "Stop, no auto-repair" if n_crit else ("Attempt repair loop" if any(
                f.code == "model_priority_mismatch" for f in findings
            ) else "No repair needed — proceed to save gate"),
        ))

        for attempt in range(1, MAX_REPAIR_ATTEMPTS + 1):
            if not Evaluator.passed(findings):
                logger.error(
                    "Agent stopping for '%s': CRITICAL finding with no automatic repair (attempt %d).",
                    self.owner.name, attempt,
                )
                actions.append(
                    f"Attempt {attempt}: a CRITICAL issue was found and the agent has no "
                    f"automatic repair for it; stopping without saving."
                )
                break

            promoted = self._promote_mismatched_tasks(plan)
            step += 1
            if not promoted:
                trace.append(TraceStep(
                    step, "TaskClassifier.classify (repair scan)",
                    f"{len(plan.skipped_tasks)} skipped task(s) vs. {len(plan.entries)} scheduled",
                    "No mismatch above the scheduled max score",
                    "No repair available — exit loop.",
                ))
                break

            logger.info(
                "Agent repair attempt %d for '%s': promoted %s to HIGH priority.",
                attempt, self.owner.name, promoted,
            )
            actions.append(
                f"Attempt {attempt}: the model rated {', '.join(promoted)} as more urgent than "
                f"what got scheduled, so the agent promoted it to HIGH priority and re-planned."
            )
            trace.append(TraceStep(
                step, "TaskClassifier.classify (repair scan)",
                f"{len(plan.skipped_tasks)} skipped task(s) vs. {len(plan.entries)} scheduled",
                f"promoted {promoted} to HIGH priority",
                f"Re-run Scheduler.generate_plan (attempt {attempt}).",
            ))
            plan = scheduler.generate_plan()
            step += 1
            trace.append(TraceStep(
                step, "Scheduler.generate_plan (re-plan)",
                f"{promoted} now HIGH priority",
                f"{len(plan.entries)} scheduled, {len(plan.skipped_tasks)} skipped",
                "Re-run Evaluator.",
            ))
            findings = Evaluator(plan).run()
            step += 1
            trace.append(TraceStep(
                step, "Evaluator.run (re-check)",
                f"re-planned entries after attempt {attempt}",
                f"{len(findings)} finding(s) remaining",
                "Loop again if still mismatched" if any(
                    f.code == "model_priority_mismatch" for f in findings
                ) else "Proceed to save gate.",
            ))

        care_tips: dict[str, str] = {}
        assessments: dict[str, TaskAssessment] = {}
        for pet, task in scheduler.collect_tasks():
            hits = self.retriever.retrieve_for_task(task.title, task.description, pet.species, top_k=1)
            if hits:
                care_tips[task.title] = hits[0].document.text
            assessments[task.title] = self.classifier.classify(task, pet, self.owner.day_start)
        step += 1
        trace.append(TraceStep(
            step, "Retriever.retrieve_for_task + TaskClassifier.classify (display)",
            f"{pending_count} pending task(s)",
            f"{len(care_tips)} care tip(s), {len(assessments)} urgency assessment(s)",
            "Attach to result for the UI/CLI.",
        ))

        saved = False
        if Evaluator.passed(findings):
            saved, findings = safe_save_plan(self.owner, plan, path=save_path, human_reviewed=human_reviewed)
            actions.append("Saved the plan." if saved else "Save blocked — pending human review of flagged tasks.")
        else:
            actions.append("Plan still has a CRITICAL issue after repair attempts — not saved.")
        step += 1
        trace.append(TraceStep(
            step, "safe_save_plan",
            f"human_reviewed={human_reviewed}",
            f"saved={saved}",
            "Done." if saved else "Blocked — needs a CRITICAL fix or human review.",
        ))

        logger.info("Agent run finished for '%s': saved=%s, findings=%d.", self.owner.name, saved, len(findings))
        return AgentResult(
            plan=plan, findings=findings, actions_taken=actions, saved=saved,
            needs_human_review=Evaluator.requires_human_review(findings),
            care_tips=care_tips, assessments=assessments, trace=trace,
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
