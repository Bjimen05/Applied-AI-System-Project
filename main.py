from pawpal_system import Owner, Pet, Task, Scheduler, Priority, Frequency

# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

alex = Owner(name="Alex", available_minutes=120, day_start=480)  # 08:00

# ---------------------------------------------------------------------------
# Pets
# ---------------------------------------------------------------------------

biscuit  = Pet(name="Biscuit",  species="Dog",    breed="Golden Retriever", age=3)
whiskers = Pet(name="Whiskers", species="Cat",    breed="Tabby",            age=5)
pebble   = Pet(name="Pebble",   species="Rabbit", breed="Holland Lop",      age=2)

alex.add_pet(biscuit)
alex.add_pet(whiskers)
alex.add_pet(pebble)

# ---------------------------------------------------------------------------
# Tasks added intentionally out of chronological order
# ---------------------------------------------------------------------------

pebble.add_task(Task(
    title="Enrichment",
    description="Free-roam time and tunnel play",
    duration_minutes=20,
    priority=Priority.LOW,
    due_time=660,   # 11:00  — added first but latest due time
))

whiskers.add_task(Task(
    title="Litter Box",
    description="Scoop and refill litter box",
    duration_minutes=5,
    priority=Priority.MEDIUM,
    due_time=600,   # 10:00
))

biscuit.add_task(Task(
    title="Morning Walk",
    description="30-minute walk around the block",
    duration_minutes=30,
    priority=Priority.HIGH,
    due_time=540,   # 09:00
    frequency=Frequency.DAILY,   # recurs every day
))

biscuit.add_task(Task(
    title="Feeding",
    description="Morning kibble — 1 cup",
    duration_minutes=10,
    priority=Priority.HIGH,
    due_time=510,   # 08:30  — added last but earliest due time
    frequency=Frequency.ONCE,    # one-off, no recurrence
))

whiskers.add_task(Task(
    title="Grooming",
    description="Brush coat and check ears",
    duration_minutes=15,
    priority=Priority.MEDIUM,
    due_time=630,   # 10:30
    frequency=Frequency.WEEKLY,  # recurs every 7 days
))

# Mark Whiskers' Litter Box complete to demonstrate the completed filter
whiskers.tasks[0].mark_complete()

# ---------------------------------------------------------------------------
# Scheduler + raw task list
# ---------------------------------------------------------------------------

scheduler = Scheduler(owner=alex)
all_tasks = scheduler.collect_all_tasks()   # includes completed and pending

# ---------------------------------------------------------------------------
# sort_by_time — show unsorted vs sorted
# ---------------------------------------------------------------------------

print("===== Tasks as added (out of order) =====")
for pet, task in all_tasks:
    status = "DONE" if task.completed else "pending"
    print(f"  {pet.name:<12} {task.title:<20} due {task.due_time // 60:02d}:{task.due_time % 60:02d}  [{status}]")

print()
print("===== sort_by_time: earliest due first =====")
for pet, task in scheduler.sort_by_time(all_tasks):
    status = "DONE" if task.completed else "pending"
    print(f"  {pet.name:<12} {task.title:<20} due {task.due_time // 60:02d}:{task.due_time % 60:02d}  [{status}]")

# ---------------------------------------------------------------------------
# filter_tasks — pending only, Biscuit only, Biscuit pending only
# ---------------------------------------------------------------------------

print()
print("===== filter: pending tasks only =====")
for pet, task in scheduler.filter_tasks(all_tasks, completed=False):
    print(f"  {pet.name:<12} {task.title}")

print()
print("===== filter: completed tasks only =====")
for pet, task in scheduler.filter_tasks(all_tasks, completed=True):
    print(f"  {pet.name:<12} {task.title}")

print()
print("===== filter: Biscuit's tasks only =====")
for pet, task in scheduler.filter_tasks(all_tasks, pet_name="Biscuit"):
    print(f"  {pet.name:<12} {task.title}")

print()
print("===== filter: Biscuit's pending tasks (both filters combined) =====")
for pet, task in scheduler.filter_tasks(all_tasks, completed=False, pet_name="Biscuit"):
    print(f"  {pet.name:<12} {task.title}")

# ---------------------------------------------------------------------------
# Generate and print full plan
# ---------------------------------------------------------------------------

print()
print("===== Today's Schedule =====")
plan = scheduler.generate_plan()
for e in plan.entries:
    start = f"{e.start_time // 60:02d}:{e.start_time % 60:02d}"
    end   = f"{e.end_time   // 60:02d}:{e.end_time   % 60:02d}"
    print(f"  {start} - {end}  {e.pet.name:<12} {e.task.title} [{e.task.priority.name}]")

if plan.skipped_tasks:
    print()
    print("Skipped:")
    for pet, task, reason in plan.skipped_tasks:
        print(f"  {pet.name:<12} {task.title} (reason: {reason})")

# ---------------------------------------------------------------------------
# Recurrence demo — mark_task_complete with timedelta
# ---------------------------------------------------------------------------

print()
print("===== Recurrence: mark tasks complete =====")

def show_pet_tasks(pet: Pet) -> None:
    for t in pet.list_tasks():
        status = "DONE" if t.completed else "pending"
        print(f"    {t.title:<22} freq={t.frequency.value:<8} due_date={t.due_date}  [{status}]")

# DAILY: Morning Walk — next occurrence should be today + 1 day
walk = biscuit.tasks[0]
print(f"\n  Completing '{walk.title}' (DAILY) for {biscuit.name}...")
next_walk = scheduler.mark_task_complete(biscuit, walk)
print(f"  timedelta used: 1 day  ->  next due_date = {next_walk.due_date}")
show_pet_tasks(biscuit)

# ONCE: Feeding — no new task should be created
feeding = biscuit.tasks[1]
print(f"\n  Completing '{feeding.title}' (ONCE) for {biscuit.name}...")
result = scheduler.mark_task_complete(biscuit, feeding)
print(f"  No recurrence — mark_task_complete returned: {result}")
show_pet_tasks(biscuit)

# WEEKLY: Grooming — next occurrence should be today + 7 days
grooming = whiskers.tasks[1]
print(f"\n  Completing '{grooming.title}' (WEEKLY) for {whiskers.name}...")
next_groom = scheduler.mark_task_complete(whiskers, grooming)
print(f"  timedelta used: 7 days  ->  next due_date = {next_groom.due_date}")
show_pet_tasks(whiskers)

# ---------------------------------------------------------------------------
# Conflict detection demo
# ---------------------------------------------------------------------------

# Build a fresh owner + pets with tasks that intentionally overlap in time.
#
#   Vet Check     : 30 min, due 09:30  → ideal window [09:00 - 09:30]
#   Bath Time     : 20 min, due 09:20  → ideal window [09:00 - 09:20]  ← overlaps Vet Check
#   Evening Walk  : 30 min, due 18:00  → ideal window [17:30 - 18:00]  ← no overlap
#
# Vet Check and Bath Time both need to start at 09:00 to hit their deadlines,
# so the owner physically cannot do both without one running over.

sam   = Owner(name="Sam", available_minutes=180, day_start=480)
buddy = Pet(name="Buddy", species="Dog", breed="Beagle", age=4)
luna  = Pet(name="Luna",  species="Cat", breed="Siamese", age=2)
sam.add_pet(buddy)
sam.add_pet(luna)

buddy.add_task(Task(
    title="Vet Check",
    description="Annual checkup",
    duration_minutes=30,
    priority=Priority.HIGH,
    due_time=570,   # 09:30  → window [09:00, 09:30]
))

luna.add_task(Task(
    title="Bath Time",
    description="Full wash and dry",
    duration_minutes=20,
    priority=Priority.HIGH,
    due_time=560,   # 09:20  → window [09:00, 09:20]  ← overlaps Vet Check
))

buddy.add_task(Task(
    title="Evening Walk",
    description="Long walk at the park",
    duration_minutes=30,
    priority=Priority.MEDIUM,
    due_time=1080,  # 18:00  → window [17:30, 18:00]  ← no overlap
))

conflict_scheduler = Scheduler(owner=sam)
conflict_tasks = conflict_scheduler.collect_all_tasks()

print()
print("===== Conflict Detection =====")
def fmt(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"

print()
print("Tasks and their ideal windows:")
for pet, task in conflict_tasks:
    start = task.due_time - task.duration_minutes
    print(f"  {pet.name:<8} {task.title:<16} window [{fmt(start)} - {fmt(task.due_time)}]")

print()
warnings = conflict_scheduler.detect_conflicts(conflict_tasks)
if warnings:
    for w in warnings:
        print(f"  {w}")
else:
    print("  No conflicts detected.")
