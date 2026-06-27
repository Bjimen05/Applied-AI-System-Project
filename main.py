from pawpal_system import Owner, Pet, Task, Scheduler, Priority

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
# Tasks  (due_time in minutes since midnight)
# ---------------------------------------------------------------------------

biscuit.add_task(Task(
    title="Morning Walk",
    description="30-minute walk around the block",
    duration_minutes=30,
    priority=Priority.HIGH,
    due_time=540,   # 09:00
))

biscuit.add_task(Task(
    title="Feeding",
    description="Morning kibble — 1 cup",
    duration_minutes=10,
    priority=Priority.HIGH,
    due_time=510,   # 08:30
))

whiskers.add_task(Task(
    title="Litter Box",
    description="Scoop and refill litter box",
    duration_minutes=5,
    priority=Priority.MEDIUM,
    due_time=600,   # 10:00
))

pebble.add_task(Task(
    title="Enrichment",
    description="Free-roam time and tunnel play",
    duration_minutes=20,
    priority=Priority.LOW,
    due_time=660,   # 11:00
))

# ---------------------------------------------------------------------------
# Generate and print plan
# ---------------------------------------------------------------------------

scheduler = Scheduler(owner=alex)
plan = scheduler.generate_plan()

print("\n===== Today's Schedule =====\n")
print(plan.display())
print()
print(plan.explain())
