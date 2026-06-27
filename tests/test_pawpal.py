from datetime import date, timedelta

from pawpal_system import (
    Frequency,
    Owner,
    Pet,
    Priority,
    Scheduler,
    SKIP_BUDGET,
    SKIP_DEADLINE,
    Task,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_task(**kwargs):
    defaults = dict(
        title="Test Task",
        description="A test task",
        duration_minutes=15,
        priority=Priority.MEDIUM,
        due_time=540,
    )
    return Task(**{**defaults, **kwargs})


def make_pet(name="Biscuit", tasks=None):
    pet = Pet(name=name, species="Dog", breed="Golden Retriever", age=3)
    for t in (tasks or []):
        pet.add_task(t)
    return pet


def make_owner(available_minutes=480, day_start=480, pets=None):
    owner = Owner(
        name="Alex",
        available_minutes=available_minutes,
        day_start=day_start,
    )
    for p in (pets or []):
        owner.add_pet(p)
    return owner


# ---------------------------------------------------------------------------
# Original tests (preserved)
# ---------------------------------------------------------------------------

def test_mark_complete_changes_status():
    task = make_task()
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_add_task_increases_pet_task_count():
    pet = Pet(name="Biscuit", species="Dog", breed="Golden Retriever", age=3)
    assert len(pet.tasks) == 0
    pet.add_task(make_task(title="Walk"))
    pet.add_task(make_task(title="Feeding"))
    assert len(pet.tasks) == 2


# ---------------------------------------------------------------------------
# Recurring task logic
# ---------------------------------------------------------------------------

def test_daily_recurrence_advances_one_day():
    base_date = date(2026, 6, 27)
    task = make_task(frequency=Frequency.DAILY, due_date=base_date)
    pet = make_pet(tasks=[task])
    scheduler = Scheduler(make_owner(pets=[pet]))

    new_task = scheduler.mark_task_complete(pet, task)

    assert new_task is not None
    assert new_task.due_date == base_date + timedelta(days=1)


def test_weekly_recurrence_advances_seven_days():
    base_date = date(2026, 6, 27)
    task = make_task(frequency=Frequency.WEEKLY, due_date=base_date)
    pet = make_pet(tasks=[task])
    scheduler = Scheduler(make_owner(pets=[pet]))

    new_task = scheduler.mark_task_complete(pet, task)

    assert new_task is not None
    assert new_task.due_date == base_date + timedelta(days=7)


def test_once_task_returns_none_and_adds_no_new_task():
    task = make_task(frequency=Frequency.ONCE)
    pet = make_pet(tasks=[task])
    scheduler = Scheduler(make_owner(pets=[pet]))

    result = scheduler.mark_task_complete(pet, task)

    assert result is None
    assert len(pet.tasks) == 1  # original only, no clone added


def test_recurring_clone_is_not_completed():
    task = make_task(frequency=Frequency.DAILY)
    pet = make_pet(tasks=[task])
    scheduler = Scheduler(make_owner(pets=[pet]))

    new_task = scheduler.mark_task_complete(pet, task)

    assert new_task.completed is False


def test_original_task_marked_complete_after_recurrence():
    task = make_task(frequency=Frequency.DAILY)
    pet = make_pet(tasks=[task])
    scheduler = Scheduler(make_owner(pets=[pet]))

    scheduler.mark_task_complete(pet, task)

    assert task.completed is True


def test_recurring_clone_added_to_pet_task_list():
    task = make_task(frequency=Frequency.DAILY)
    pet = make_pet(tasks=[task])
    scheduler = Scheduler(make_owner(pets=[pet]))

    new_task = scheduler.mark_task_complete(pet, task)

    assert new_task in pet.tasks
    assert len(pet.tasks) == 2


# ---------------------------------------------------------------------------
# Sorting (sort_by_time)
# ---------------------------------------------------------------------------

def test_sort_by_time_orders_ascending():
    pet = make_pet()
    t1 = make_task(title="Late",  due_time=900)
    t2 = make_task(title="Early", due_time=480)
    t3 = make_task(title="Mid",   due_time=660)
    scheduler = Scheduler(make_owner(pets=[pet]))

    result = scheduler.sort_by_time([(pet, t1), (pet, t2), (pet, t3)])
    due_times = [t.due_time for _, t in result]

    assert due_times == [480, 660, 900]


def test_sort_by_time_empty_list():
    scheduler = Scheduler(make_owner())
    assert scheduler.sort_by_time([]) == []


def test_sort_by_time_single_task_unchanged():
    pet = make_pet()
    task = make_task(due_time=600)
    scheduler = Scheduler(make_owner(pets=[pet]))

    result = scheduler.sort_by_time([(pet, task)])
    assert result == [(pet, task)]


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

def test_overlapping_windows_detected():
    pet = make_pet()
    # Task A window: [510, 600], Task B window: [510, 570] — overlap
    task_a = make_task(title="Walk",  due_time=600, duration_minutes=90)
    task_b = make_task(title="Feed",  due_time=570, duration_minutes=60)
    scheduler = Scheduler(make_owner(pets=[pet]))

    warnings = scheduler.detect_conflicts([(pet, task_a), (pet, task_b)])

    assert len(warnings) == 1
    assert "Walk" in warnings[0]
    assert "Feed" in warnings[0]


def test_non_overlapping_windows_no_conflict():
    pet = make_pet()
    # Task A window: [480, 540], Task B window: [540, 600] — touch but no overlap
    task_a = make_task(title="Walk", due_time=540, duration_minutes=60)
    task_b = make_task(title="Feed", due_time=600, duration_minutes=60)
    scheduler = Scheduler(make_owner(pets=[pet]))

    warnings = scheduler.detect_conflicts([(pet, task_a), (pet, task_b)])

    assert warnings == []


def test_single_task_no_conflict():
    pet = make_pet()
    task = make_task()
    scheduler = Scheduler(make_owner(pets=[pet]))

    assert scheduler.detect_conflicts([(pet, task)]) == []


def test_empty_task_list_no_conflict():
    scheduler = Scheduler(make_owner())
    assert scheduler.detect_conflicts([]) == []


def test_completed_tasks_excluded_from_conflict_check():
    pet = make_pet()
    # Two overlapping tasks, but one is already done
    task_a = make_task(title="Walk", due_time=600, duration_minutes=90)
    task_b = make_task(title="Feed", due_time=570, duration_minutes=60)
    task_b.mark_complete()
    scheduler = Scheduler(make_owner(pets=[pet]))

    warnings = scheduler.detect_conflicts([(pet, task_a), (pet, task_b)])

    assert warnings == []


# ---------------------------------------------------------------------------
# generate_plan — deadline and budget skipping
# ---------------------------------------------------------------------------

def test_task_skipped_when_it_misses_deadline():
    # day_start=480, duration=120 → finish=600 > due_time=540 → skip
    task = make_task(duration_minutes=120, due_time=540, priority=Priority.HIGH)
    pet = make_pet(tasks=[task])
    owner = make_owner(available_minutes=480, day_start=480, pets=[pet])
    plan = Scheduler(owner).generate_plan()

    assert len(plan.entries) == 0
    assert len(plan.skipped_tasks) == 1
    _, skipped_task, reason = plan.skipped_tasks[0]
    assert skipped_task is task
    assert reason == SKIP_DEADLINE


def test_task_skipped_when_budget_exhausted():
    task = make_task(duration_minutes=60, due_time=900)
    pet = make_pet(tasks=[task])
    owner = make_owner(available_minutes=30, day_start=480, pets=[pet])
    plan = Scheduler(owner).generate_plan()

    assert len(plan.entries) == 0
    _, skipped_task, reason = plan.skipped_tasks[0]
    assert skipped_task is task
    assert reason == SKIP_BUDGET


def test_task_fits_when_duration_equals_remaining_budget():
    # Exactly on the budget boundary — should be scheduled, not skipped
    task = make_task(duration_minutes=60, due_time=900)
    pet = make_pet(tasks=[task])
    owner = make_owner(available_minutes=60, day_start=480, pets=[pet])
    plan = Scheduler(owner).generate_plan()

    assert len(plan.entries) == 1
    assert plan.skipped_tasks == []


def test_task_fits_when_finish_equals_due_time():
    # clock(480) + duration(60) = 540 == due_time(540); condition is >, so should schedule
    task = make_task(duration_minutes=60, due_time=540)
    pet = make_pet(tasks=[task])
    owner = make_owner(available_minutes=480, day_start=480, pets=[pet])
    plan = Scheduler(owner).generate_plan()

    assert len(plan.entries) == 1
    assert plan.skipped_tasks == []


def test_zero_budget_skips_all_tasks():
    task = make_task(duration_minutes=15, due_time=900)
    pet = make_pet(tasks=[task])
    owner = make_owner(available_minutes=0, day_start=480, pets=[pet])
    plan = Scheduler(owner).generate_plan()

    assert plan.entries == []
    assert len(plan.skipped_tasks) == 1


def test_no_pets_produces_empty_plan():
    owner = make_owner(pets=[])
    plan = Scheduler(owner).generate_plan()

    assert plan.entries == []
    assert plan.skipped_tasks == []


# ---------------------------------------------------------------------------
# generate_plan — priority and urgency ordering
# ---------------------------------------------------------------------------

def test_high_priority_scheduled_before_low_priority():
    pet = make_pet()
    low  = make_task(title="Low",  priority=Priority.LOW,  due_time=900, duration_minutes=30)
    high = make_task(title="High", priority=Priority.HIGH, due_time=900, duration_minutes=30)
    pet.add_task(low)
    pet.add_task(high)
    owner = make_owner(available_minutes=30, day_start=480, pets=[pet])
    plan = Scheduler(owner).generate_plan()

    # Only one fits; it should be the HIGH priority task
    assert len(plan.entries) == 1
    assert plan.entries[0].task.title == "High"


def test_urgent_low_priority_boosted_over_non_urgent_medium():
    pet = make_pet()
    # day_start=480, urgency_window=540
    # Boost lifts one tier: urgent LOW (3→2) beats non-urgent MEDIUM (2), but not HIGH (1)
    urgent_low     = make_task(title="UrgentLow",     priority=Priority.LOW,    due_time=530, duration_minutes=10)
    distant_medium = make_task(title="DistantMedium", priority=Priority.MEDIUM, due_time=900, duration_minutes=10)
    pet.add_task(distant_medium)
    pet.add_task(urgent_low)
    owner = make_owner(available_minutes=10, day_start=480, pets=[pet])
    plan = Scheduler(owner).generate_plan()

    # Budget only fits one; urgency boost lifts urgent_low above distant_medium
    assert len(plan.entries) == 1
    assert plan.entries[0].task.title == "UrgentLow"


# ---------------------------------------------------------------------------
# filter_tasks
# ---------------------------------------------------------------------------

def test_filter_pending_excludes_completed():
    pet = make_pet()
    pending   = make_task(title="Pending")
    completed = make_task(title="Done")
    completed.mark_complete()
    scheduler = Scheduler(make_owner(pets=[pet]))
    tasks = [(pet, pending), (pet, completed)]

    result = scheduler.filter_tasks(tasks, completed=False)

    titles = [t.title for _, t in result]
    assert "Pending" in titles
    assert "Done" not in titles


def test_filter_completed_excludes_pending():
    pet = make_pet()
    pending   = make_task(title="Pending")
    completed = make_task(title="Done")
    completed.mark_complete()
    scheduler = Scheduler(make_owner(pets=[pet]))
    tasks = [(pet, pending), (pet, completed)]

    result = scheduler.filter_tasks(tasks, completed=True)

    titles = [t.title for _, t in result]
    assert "Done" in titles
    assert "Pending" not in titles


def test_filter_by_pet_name_case_insensitive():
    pet_a = make_pet(name="Buddy")
    pet_b = make_pet(name="Luna")
    task_a = make_task(title="A")
    task_b = make_task(title="B")
    scheduler = Scheduler(make_owner(pets=[pet_a, pet_b]))
    tasks = [(pet_a, task_a), (pet_b, task_b)]

    result = scheduler.filter_tasks(tasks, pet_name="buddy")

    assert len(result) == 1
    assert result[0][0].name == "Buddy"


def test_filter_combined_status_and_pet_name():
    pet_a = make_pet(name="Buddy")
    pet_b = make_pet(name="Luna")
    done  = make_task(title="BuddyDone")
    done.mark_complete()
    active = make_task(title="BuddyActive")
    luna_task = make_task(title="LunaTask")
    scheduler = Scheduler(make_owner())
    tasks = [(pet_a, done), (pet_a, active), (pet_b, luna_task)]

    result = scheduler.filter_tasks(tasks, completed=False, pet_name="Buddy")

    assert len(result) == 1
    assert result[0][1].title == "BuddyActive"


def test_filter_unknown_pet_name_returns_empty():
    pet = make_pet(name="Buddy")
    task = make_task()
    scheduler = Scheduler(make_owner(pets=[pet]))

    result = scheduler.filter_tasks([(pet, task)], pet_name="NoSuchPet")

    assert result == []


# ---------------------------------------------------------------------------
# total_time_used
# ---------------------------------------------------------------------------

def test_total_time_used_sums_scheduled_durations():
    task1 = make_task(duration_minutes=30, due_time=900)
    task2 = make_task(duration_minutes=45, due_time=900)
    pet = make_pet(tasks=[task1, task2])
    owner = make_owner(available_minutes=480, day_start=480, pets=[pet])
    plan = Scheduler(owner).generate_plan()

    assert plan.total_time_used() == 75


def test_total_time_used_empty_plan():
    owner = make_owner(pets=[])
    plan = Scheduler(owner).generate_plan()

    assert plan.total_time_used() == 0
