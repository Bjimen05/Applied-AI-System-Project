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

### UI Features

The Streamlit app (`app.py`) gives you a single-page interface with three main areas:

- **Owner & Pet Setup** — Enter the owner's name, daily time budget (minutes), and the hour their day starts. Add a pet with name, species, breed, and age. Resubmitting the form updates settings without wiping existing tasks.
- **Add a Task** — Choose a title, duration, priority (HIGH / MEDIUM / LOW), deadline hour, and whether the task repeats (ONCE / DAILY / WEEKLY). Click "Add task" to attach it to the active pet.
- **Task list** — All pending tasks for the active pet are shown in a table sorted chronologically by due time. If any two tasks have overlapping ideal windows, a conflict warning appears immediately below the table.
- **Build Schedule** — Click "Generate schedule" to run the scheduler. The result shows a time-slotted table of scheduled tasks, a summary of minutes used vs. available, and a warning for each skipped task explaining whether it was dropped due to a missed deadline or an exhausted budget. A "Why was this plan chosen?" expander shows the full plain-English reasoning.

### Example Workflow

1. Set owner **Jordan**, 120 available minutes, day start at 08:00.
2. Add pet **Mochi** (dog).
3. Add task: *Morning walk*, 30 min, HIGH priority, due by 09:00, repeats DAILY.
4. Add task: *Feeding*, 10 min, HIGH priority, due by 08:30, repeats ONCE.
5. The task table re-renders sorted by due time — Feeding (08:30) appears above Morning walk (09:00).
6. Click **Generate schedule**. The scheduler fits both tasks within the budget and slots them back-to-back starting at 08:00.
7. After completing Morning walk in real life, calling `mark_task_complete` creates a new instance due tomorrow automatically — the DAILY recurrence is handled without any manual re-entry.

### Key Scheduler Behaviors Shown

| Behavior | What you see |
|---|---|
| Chronological sort (`sort_by_time`) | Task table always lists earliest deadlines first, regardless of the order tasks were added |
| Priority + urgency sort (`_sort_tasks`) | HIGH priority tasks are placed first in the generated plan; a LOW priority task due within 60 min of day start is boosted one tier |
| Conflict warnings (`detect_conflicts`) | A yellow `st.warning` appears under the task table when two tasks' ideal windows overlap |
| Deadline skip | A skipped task's warning names the deadline it would have missed |
| Budget skip | A skipped task's warning states the budget was exhausted |
| Recurring tasks (`mark_task_complete`) | DAILY advances `due_date` by 1 day; WEEKLY by 7 days; ONCE produces no new task |

### Sample CLI Output

Running `python main.py` exercises the full backend without the UI:

```
===== Tasks as added (out of order) =====
  Biscuit      Morning Walk         due 09:00  [pending]
  Biscuit      Feeding              due 08:30  [pending]
  Whiskers     Litter Box           due 10:00  [DONE]
  Whiskers     Grooming             due 10:30  [pending]
  Pebble       Enrichment           due 11:00  [pending]

===== sort_by_time: earliest due first =====
  Biscuit      Feeding              due 08:30  [pending]
  Biscuit      Morning Walk         due 09:00  [pending]
  Whiskers     Litter Box           due 10:00  [DONE]
  Whiskers     Grooming             due 10:30  [pending]
  Pebble       Enrichment           due 11:00  [pending]

===== filter: pending tasks only =====
  Biscuit      Morning Walk
  Biscuit      Feeding
  Whiskers     Grooming
  Pebble       Enrichment

===== filter: completed tasks only =====
  Whiskers     Litter Box

===== filter: Biscuit's tasks only =====
  Biscuit      Morning Walk
  Biscuit      Feeding

===== filter: Biscuit's pending tasks (both filters combined) =====
  Biscuit      Morning Walk
  Biscuit      Feeding

===== Today's Schedule =====
  08:00 - 08:10  Biscuit      Feeding [HIGH]
  08:10 - 08:40  Biscuit      Morning Walk [HIGH]
  08:40 - 08:55  Whiskers     Grooming [MEDIUM]
  08:55 - 09:15  Pebble       Enrichment [LOW]

===== Recurrence: mark tasks complete =====

  Completing 'Morning Walk' (DAILY) for Biscuit...
  timedelta used: 1 day  ->  next due_date = 2026-06-28
    Morning Walk           freq=daily    due_date=2026-06-27  [DONE]
    Feeding                freq=once     due_date=2026-06-27  [pending]
    Morning Walk           freq=daily    due_date=2026-06-28  [pending]

  Completing 'Feeding' (ONCE) for Biscuit...
  No recurrence — mark_task_complete returned: None
    Morning Walk           freq=daily    due_date=2026-06-27  [DONE]
    Feeding                freq=once     due_date=2026-06-27  [DONE]
    Morning Walk           freq=daily    due_date=2026-06-28  [pending]

  Completing 'Grooming' (WEEKLY) for Whiskers...
  timedelta used: 7 days  ->  next due_date = 2026-07-04
    Litter Box             freq=once     due_date=2026-06-27  [DONE]
    Grooming               freq=weekly   due_date=2026-06-27  [DONE]
    Grooming               freq=weekly   due_date=2026-07-04  [pending]

===== Conflict Detection =====

Tasks and their ideal windows:
  Buddy    Vet Check        window [09:00 - 09:30]
  Buddy    Evening Walk     window [17:30 - 18:00]
  Luna     Bath Time        window [09:00 - 09:20]

  WARNING: 'Vet Check' (Buddy) [09:00-09:30] overlaps with 'Bath Time' (Luna) [09:00-09:20]
```
