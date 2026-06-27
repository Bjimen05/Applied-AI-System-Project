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

Run the full test suite from the project root:

```bash
python -m pytest tests/test_pawpal.py -v
```

The tests cover:

- **Recurring tasks** — DAILY advances one day, WEEKLY advances seven days, ONCE produces no clone, and the new task is always reset to `completed=False`
- **Sorting** — `sort_by_time` orders tasks by `due_time` ascending, handles empty lists and single-item lists
- **Conflict detection** — overlapping ideal windows are flagged, non-overlapping and completed tasks are ignored
- **Scheduling / `generate_plan`** — tasks are skipped with the correct reason (`"deadline"` or `"budget"`), boundary conditions (duration exactly equals budget or due time) are handled correctly, and priority + urgency ordering is enforced
- **Filtering** — `filter_tasks` handles pending/completed status, case-insensitive pet name matching, combined filters, and unknown names

```
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.0.3, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\Brandon\Documents\GitHub\ai110-module2show-pawpal-starter
plugins: anyio-4.13.0
collecting ... collected 31 items

tests/test_pawpal.py::test_mark_complete_changes_status PASSED           [  3%]
tests/test_pawpal.py::test_add_task_increases_pet_task_count PASSED      [  6%]
tests/test_pawpal.py::test_daily_recurrence_advances_one_day PASSED      [  9%]
tests/test_pawpal.py::test_weekly_recurrence_advances_seven_days PASSED  [ 12%]
tests/test_pawpal.py::test_once_task_returns_none_and_adds_no_new_task PASSED [ 16%]
tests/test_pawpal.py::test_recurring_clone_is_not_completed PASSED       [ 19%]
tests/test_pawpal.py::test_original_task_marked_complete_after_recurrence PASSED [ 22%]
tests/test_pawpal.py::test_recurring_clone_added_to_pet_task_list PASSED [ 25%]
tests/test_pawpal.py::test_sort_by_time_orders_ascending PASSED          [ 29%]
tests/test_pawpal.py::test_sort_by_time_empty_list PASSED                [ 32%]
tests/test_pawpal.py::test_sort_by_time_single_task_unchanged PASSED     [ 35%]
tests/test_pawpal.py::test_overlapping_windows_detected PASSED           [ 38%]
tests/test_pawpal.py::test_non_overlapping_windows_no_conflict PASSED    [ 41%]
tests/test_pawpal.py::test_single_task_no_conflict PASSED                [ 45%]
tests/test_pawpal.py::test_empty_task_list_no_conflict PASSED            [ 48%]
tests/test_pawpal.py::test_completed_tasks_excluded_from_conflict_check PASSED [ 51%]
tests/test_pawpal.py::test_task_skipped_when_it_misses_deadline PASSED   [ 54%]
tests/test_pawpal.py::test_task_skipped_when_budget_exhausted PASSED     [ 58%]
tests/test_pawpal.py::test_task_fits_when_duration_equals_remaining_budget PASSED [ 61%]
tests/test_pawpal.py::test_task_fits_when_finish_equals_due_time PASSED  [ 64%]
tests/test_pawpal.py::test_zero_budget_skips_all_tasks PASSED            [ 67%]
tests/test_pawpal.py::test_no_pets_produces_empty_plan PASSED            [ 70%]
tests/test_pawpal.py::test_high_priority_scheduled_before_low_priority PASSED [ 74%]
tests/test_pawpal.py::test_urgent_low_priority_boosted_over_non_urgent_medium PASSED [ 77%]
tests/test_pawpal.py::test_filter_pending_excludes_completed PASSED      [ 80%]
tests/test_pawpal.py::test_filter_completed_excludes_pending PASSED      [ 83%]
tests/test_pawpal.py::test_filter_by_pet_name_case_insensitive PASSED    [ 87%]
tests/test_pawpal.py::test_filter_combined_status_and_pet_name PASSED    [ 90%]
tests/test_pawpal.py::test_filter_unknown_pet_name_returns_empty PASSED  [ 93%]
tests/test_pawpal.py::test_total_time_used_sums_scheduled_durations PASSED [ 96%]
tests/test_pawpal.py::test_total_time_used_empty_plan PASSED             [100%]

============================= 31 passed in 0.03s ==============================

My confidence level is 5 stars based on my test results
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
