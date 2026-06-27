# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
Daily Plan for Alex — 2026-06-26
──────────────────────────────────────────────────
  08:00 – 08:10  Biscuit      Feeding (10 min) [HIGH]
  08:10 – 08:40  Biscuit      Morning Walk (30 min) [HIGH]
  08:40 – 08:45  Whiskers     Litter Box (5 min) [MEDIUM]
  08:45 – 09:05  Pebble       Enrichment (20 min) [LOW]
──────────────────────────────────────────────────
  Total: 65 / 120 min used
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```

## 📐 Smarter Scheduling

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Priority + urgency sort | `Scheduler._sort_tasks` | Sorts by priority (HIGH=1, LOW=3), then deadline, then duration. Tasks due within 60 min of `day_start` get their priority rank boosted by one tier automatically. |

| Chronological sort | `Scheduler.sort_by_time` | Returns tasks sorted by `due_time` (minutes since midnight) ascending — useful for display and inspection. |

| Status / pet filter | `Scheduler.filter_tasks` | Filters a task list by `completed` status, `pet_name`, or both combined. Keyword-only args prevent accidental positional misuse. |

| Deadline feasibility | `Scheduler.generate_plan` | Before placing a task, checks that `clock + duration <= due_time`. Tasks that would finish after their deadline are skipped with reason `"deadline"` instead of `"budget"`. |

| Conflict detection | `Scheduler.detect_conflicts` | Computes each task's ideal window `[due_time - duration, due_time]` and checks all pairs for overlap. Returns a warning string per conflicting pair; returns an empty list when the schedule is clean. |

| Recurring tasks | `Scheduler.mark_task_complete` | Marks a task done and, if `frequency` is `DAILY` or `WEEKLY`, uses `timedelta(days=1)` or `timedelta(days=7)` to create a new instance with the next `due_date` automatically added to the pet. `Frequency.ONCE` tasks are not repeated. |

| Collect all tasks | `Scheduler.collect_all_tasks` | Returns every task across all pets regardless of completion status — needed to use `filter_tasks` across both pending and done tasks. |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
