"""Regenerates the tabulate-rendered agent reasoning traces in
ai_interactions.md (Stretch: Agentic Workflow Enhancement). Re-run this
after any change to agent.py's trace output to keep the committed log
in sync with the actual code: `python gen_traces.py`.
"""
import os
import sys
sys.stdout.reconfigure(encoding="utf-8")

from datetime import date, timedelta
import tempfile
from tabulate import tabulate
from pawpal_system import Owner, Pet, Priority, Task
from retriever import Retriever
from agent import PawPalAgent

tmpdir = tempfile.gettempdir()
HEADERS = ["Step", "Tool Called", "Input", "Output", "Decision"]


def phase_table(trace, start, end):
    rows = [
        [t.step, t.tool, t.input_summary, t.output_summary, t.decision]
        for t in trace if start <= t.step <= end
    ]
    return tabulate(rows, headers=HEADERS, tablefmt="github")


def render(title, intro, trace, phases):
    out = [f"### {title}", "", intro, ""]
    for label, (start, end) in phases:
        out.append(f"**{label}**")
        out.append("")
        out.append(phase_table(trace, start, end))
        out.append("")
        out.append("---")
        out.append("")
    return "\n".join(out)


owner = Owner(name="Priya", available_minutes=15, day_start=480)
pet = Pet(name="Max", species="dog", breed="Mixed", age=4)
owner.add_pet(pet)
walk = Task("Walk", "Evening walk", 15, Priority.HIGH, due_time=700)
groom = Task("Grooming", "Brush and nail trim", 15, Priority.MEDIUM, due_time=650)
groom.due_date = date.today() - timedelta(days=1)
pet.add_task(walk)
pet.add_task(groom)
agent = PawPalAgent(owner, retriever=Retriever([]))
result = agent.run(human_reviewed=True, save_path=os.path.join(tmpdir, "scenario1.json"))

section1 = render(
    "Scenario 1 \u2014 priority-mismatch repair loop (owner: Priya)",
    "A MEDIUM, overdue \"Grooming\" task is initially skipped in favor of a HIGH \"Walk\" task "
    "with no time pressure. The agent notices the specialized model rates the skipped task as "
    "more urgent, promotes it, and re-plans \u2014 changing which task actually gets scheduled.",
    result.trace,
    [("Phase 1 \u2014 generate & evaluate", (1, 2)),
     ("Phase 2 \u2014 repair loop", (3, 6)),
     ("Phase 3 \u2014 display & save", (7, 8))],
)
section1 += "**Result:** `Grooming` ends up scheduled instead of `Walk` \u2014 a real behavior change driven by the reasoning chain, not just a logged warning.\n"

owner2 = Owner(name="Sam", available_minutes=180, day_start=480)
buddy = Pet(name="Buddy", species="dog", breed="Beagle", age=4)
owner2.add_pet(buddy)
buddy.add_task(Task("Vet Check", "Annual checkup", 30, Priority.HIGH, due_time=570))
agent2 = PawPalAgent(owner2)
result2 = agent2.run(human_reviewed=False, save_path=os.path.join(tmpdir, "scenario2.json"))

section2 = render(
    "Scenario 2 \u2014 high-risk task blocks save pending human review (owner: Sam)",
    "A \"Vet Check\" task is scheduled cleanly (no repair needed), but the Evaluator flags it as "
    "health-related, so the agent's save gate blocks persistence until a human explicitly approves it.",
    result2.trace,
    [("Phase 1 \u2014 generate & evaluate", (1, 2)),
     ("Phase 2 \u2014 repair scan (no-op)", (3, 3)),
     ("Phase 3 \u2014 display & save", (4, 5))],
)
section2 += "**Result:** nothing is written to disk until `agent.run(human_reviewed=True, ...)` is called again \u2014 the same trace structure, with step 5's output flipping to `saved=True`.\n"

header = (
    "## Agentic Reasoning Trace (Stretch: Agentic Workflow Enhancement)\n\n"
    "> `PawPalAgent.run()` (in `agent.py`) performs multi-step reasoning with real tool calls "
    "\u2014 Scheduler, Evaluator, TaskClassifier, Retriever, and `safe_save_plan` \u2014 and decides "
    "what to do next based on each tool's output (repair, stop, or save). Every call is recorded "
    "as a `TraceStep` (step number, tool called, input, output, decision). Both traces below are "
    "the verbatim output of a script (`gen_traces.py`) that actually runs the agent and renders "
    "the trace with `tabulate` \u2014 see "
    "`tests/test_agent.py::test_agent_trace_records_repair_loop_steps` for the automated check "
    "that this structure holds.\n\n"
)

full = header + section1 + "\n---\n\n" + section2

repo = os.path.dirname(os.path.abspath(__file__))
ai_interactions_path = os.path.join(repo, "ai_interactions.md")
marker = "<!-- Your conclusion -->"

with open(ai_interactions_path, "r", encoding="utf-8") as f:
    existing = f.read()

idx = existing.index(marker) + len(marker)
new_content = existing[:idx].rstrip("\n") + "\n\n---\n\n" + full

with open(ai_interactions_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("WROTE:", ai_interactions_path)
