# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agent Workflow (SF7)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

I asked Claude Code (claude-sonnet-4-6) to add a third scheduling algorithm capability to the existing `Scheduler` class — specifically a **weighted prioritization** system that goes beyond the binary urgency-boost in `_sort_tasks`. The goal was to blend priority level, deadline pressure, and task duration efficiency into a continuous numeric score so tasks could be ranked with more nuance than a fixed enum.

**What did the agent do?**

1. **Read `pawpal_system.py`** to understand the existing `_sort_tasks` logic — it already sorted by `(priority_rank, due_time, duration_minutes)` with a one-tier urgency boost for tasks due within 60 minutes of `day_start`.
2. **Identified the gap**: the existing sort was discrete (enum ranks 1–3 with one possible boost), so two HIGH tasks could only be broken by deadline, not by how far away or how short they were — there was no way to express "this HIGH task is much more urgent than that one."
3. **Designed a scoring formula** with three additive signals:
   - *Priority base*: HIGH=30, MEDIUM=20, LOW=10 — keeps priority dominant
   - *Urgency bonus* (0–10): `(window - minutes_until_due) / window × 10`, normalized over an 8-hour window — tasks due soon score closer to 10
   - *Efficiency bonus* (0–5): `(60 - duration) / 60 × 5`, capped at tasks under 60 min — shorter tasks get a small lift
4. **Added two methods** to `Scheduler` in `pawpal_system.py`:
   - `score_task(task) → float` — returns the combined score for one task
   - `sort_by_weight(tasks) → list` — sorts by score descending so the highest-value task comes first
5. **Verified the formula behavior** mentally: a HIGH task due immediately with 5-minute duration would score ~45, while a LOW task due in 8 hours with 90-minute duration would score ~10 — the separation is meaningful and proportional.

**What did you have to verify or fix manually?**

- **Efficiency bonus cap**: the formula uses `(60 - duration) / 60`, which goes negative for tasks longer than 60 minutes. I confirmed the agent wrapped this in `max(0.0, ...)` so long tasks simply score 0 on that component rather than pulling their total score below the base — a subtle correctness issue worth checking.
- **Urgency normalization when `due_time < day_start`**: a task whose deadline has already passed before the day starts would make `minutes_until_due` negative, inflating the urgency bonus above 10. The agent used `max(task.due_time - self.owner.day_start, 0)` to clamp this, which is the right call — but it was something to confirm by reading the code rather than trusting the summary.
- **Integration with `generate_plan`**: `sort_by_weight` is a standalone method, not wired into `generate_plan` automatically. That was intentional — swapping the sort strategy in the plan generator would be a separate decision — but it means `sort_by_weight` is currently a display/inspection tool rather than part of the scheduling pipeline. Worth deciding whether to expose a `strategy` parameter to `generate_plan` in a future iteration.

---

## Prompt Comparison (SF11)

> Compare two different prompts (or two different models) on the same task.

| | Option A | Option B |
|-|----------|----------|
| **Model / tool used** | | |

* Claude  |   Cursor

| **Prompt** | | |


*Extend my Scheduler to detect when two tasks (for the same or different pets) overlap in time. Instead of crashing, return a warning message about the conflict.
Update main.py with two tasks scheduled at the same time and confirm that the scheduler detects and prints the warning.

| **Response summary** | | |

*Added a detect_conflicts() method, updated main.py with sample tasks, ran the program, fixed a small _fmt_time issue, and verified the warning was printed. |  Added a detect_conflicts() method, explained the overlap algorithm, updated main.py with sample tasks, and confirmed the warning was detected correctly.

| **What was useful** | | |

*Automatically edited multiple files, tested the code, fixed an error, and verified the final output. |  Clearly explained the conflict detection algorithm and why the overlap logic works.

| **Problems noticed** | | |

*An edit to main.py initially failed and _fmt_time caused an error that needed to be fixed. | Did not show as much debugging or verification as Claude.

| **Decision** | | |

*It verified the implementation by running the code and fixing issues before finishing. |  Good explanation and implementation, but less evidence of testing and debugging.


**Which approach did you use in your final implementation and why?**

I chosen Claude because it can explain what is the issue and how it will fix it, as well correct itself if it made a error, and verify it.

<!-- Your conclusion -->
