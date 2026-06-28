import sys
sys.stdout.reconfigure(encoding="utf-8")

from colorama import Fore, Style, init as colorama_init
from tabulate import tabulate

from pawpal_system import Owner, Pet, Task, Scheduler, Priority, Frequency

colorama_init(autoreset=True)

# ---------------------------------------------------------------------------
# Display helpers — emoji + color
# ---------------------------------------------------------------------------

SPECIES_EMOJI = {
    "dog":    "🐕",
    "cat":    "🐈",
    "rabbit": "🐇",
}

PRIORITY_STYLE = {
    Priority.HIGH:   (Fore.RED    + "🔴 HIGH"  , "🔴 HIGH"),
    Priority.MEDIUM: (Fore.YELLOW + "🟡 MED"   , "🟡 MED"),
    Priority.LOW:    (Fore.GREEN  + "🟢 LOW"   , "🟢 LOW"),
}

FREQ_EMOJI = {
    Frequency.ONCE:   "1️⃣  once  ",
    Frequency.DAILY:  "🔁 daily ",
    Frequency.WEEKLY: "📅 weekly",
}


def species_icon(species: str) -> str:
    return SPECIES_EMOJI.get(species.lower(), "🐾")


def priority_label(p: Priority) -> str:
    colored, _ = PRIORITY_STYLE[p]
    return colored + Style.RESET_ALL


def status_label(completed: bool) -> str:
    if completed:
        return Fore.GREEN + "✅ done   " + Style.RESET_ALL
    return Fore.YELLOW + "⏳ pending" + Style.RESET_ALL


def section(title: str) -> None:
    print()
    print(Fore.CYAN + Style.BRIGHT + f"{'─' * 4} {title} {'─' * (50 - len(title))}" + Style.RESET_ALL)


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
    due_time=660,
))

whiskers.add_task(Task(
    title="Litter Box",
    description="Scoop and refill litter box",
    duration_minutes=5,
    priority=Priority.MEDIUM,
    due_time=600,
))

biscuit.add_task(Task(
    title="Morning Walk",
    description="30-minute walk around the block",
    duration_minutes=30,
    priority=Priority.HIGH,
    due_time=540,
    frequency=Frequency.DAILY,
))

biscuit.add_task(Task(
    title="Feeding",
    description="Morning kibble — 1 cup",
    duration_minutes=10,
    priority=Priority.HIGH,
    due_time=510,
    frequency=Frequency.ONCE,
))

whiskers.add_task(Task(
    title="Grooming",
    description="Brush coat and check ears",
    duration_minutes=15,
    priority=Priority.MEDIUM,
    due_time=630,
    frequency=Frequency.WEEKLY,
))

# Mark Litter Box complete to demonstrate the completed filter
whiskers.tasks[0].mark_complete()

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

scheduler = Scheduler(owner=alex)
all_tasks = scheduler.collect_all_tasks()

# ---------------------------------------------------------------------------
# Task table — as added (unsorted)
# ---------------------------------------------------------------------------

def _fmt(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def task_rows(pairs):
    rows = []
    for pet, task in pairs:
        icon = species_icon(pet.species)
        rows.append([
            f"{icon} {pet.name}",
            task.title,
            priority_label(task.priority),
            _fmt(task.due_time),
            f"{task.duration_minutes} min",
            FREQ_EMOJI[task.frequency],
            status_label(task.completed),
        ])
    return rows


TASK_HEADERS = ["Pet", "Task", "Priority", "Due", "Duration", "Repeats", "Status"]

section("Tasks as added (out of order)")
print(tabulate(task_rows(all_tasks), headers=TASK_HEADERS, tablefmt="rounded_outline"))

section("sort_by_time: earliest due first")
print(tabulate(task_rows(scheduler.sort_by_time(all_tasks)), headers=TASK_HEADERS, tablefmt="rounded_outline"))

# ---------------------------------------------------------------------------
# Filtered views
# ---------------------------------------------------------------------------

section("filter: pending tasks only")
pending_rows = [
    [f"{species_icon(p.species)} {p.name}", t.title, priority_label(t.priority)]
    for p, t in scheduler.filter_tasks(all_tasks, completed=False)
]
print(tabulate(pending_rows, headers=["Pet", "Task", "Priority"], tablefmt="simple_outline"))

section("filter: completed tasks only")
done_rows = [
    [f"{species_icon(p.species)} {p.name}", t.title, priority_label(t.priority)]
    for p, t in scheduler.filter_tasks(all_tasks, completed=True)
]
print(tabulate(done_rows, headers=["Pet", "Task", "Priority"], tablefmt="simple_outline"))

section("filter: Biscuit's pending tasks (combined)")
biscuit_rows = [
    [f"{species_icon(p.species)} {p.name}", t.title, priority_label(t.priority), _fmt(t.due_time)]
    for p, t in scheduler.filter_tasks(all_tasks, completed=False, pet_name="Biscuit")
]
print(tabulate(biscuit_rows, headers=["Pet", "Task", "Priority", "Due"], tablefmt="simple_outline"))

# ---------------------------------------------------------------------------
# Daily schedule
# ---------------------------------------------------------------------------

section("Today's Schedule")
plan = scheduler.generate_plan()

schedule_rows = []
for e in plan.entries:
    icon = species_icon(e.pet.species)
    slot = f"{_fmt(e.start_time)} – {_fmt(e.end_time)}"
    schedule_rows.append([
        slot,
        f"{icon} {e.pet.name}",
        e.task.title,
        priority_label(e.task.priority),
        f"{e.task.duration_minutes} min",
    ])

print(tabulate(schedule_rows, headers=["Time Slot", "Pet", "Task", "Priority", "Duration"], tablefmt="rounded_outline"))
print(Fore.CYAN + f"  Total: {plan.total_time_used()} / {alex.available_minutes} min used" + Style.RESET_ALL)

if plan.skipped_tasks:
    print()
    skipped_rows = [
        [f"{species_icon(p.species)} {p.name}", t.title, priority_label(t.priority),
         Fore.RED + reason + Style.RESET_ALL]
        for p, t, reason in plan.skipped_tasks
    ]
    print(tabulate(skipped_rows, headers=["Pet", "Task", "Priority", "Skipped reason"], tablefmt="simple_outline"))

# ---------------------------------------------------------------------------
# Recurrence demo
# ---------------------------------------------------------------------------

section("Recurrence: mark tasks complete")

def show_pet_tasks(pet: Pet) -> None:
    rows = [
        [t.title, FREQ_EMOJI[t.frequency], str(t.due_date), status_label(t.completed)]
        for t in pet.list_tasks()
    ]
    print(tabulate(rows, headers=["Task", "Repeats", "Due date", "Status"], tablefmt="simple"))

walk = biscuit.tasks[0]
print(f"\n  {Fore.YELLOW}Completing '{walk.title}' (DAILY) for {biscuit.name}...{Style.RESET_ALL}")
next_walk = scheduler.mark_task_complete(biscuit, walk)
print(f"  timedelta: 1 day  →  next due_date = {Fore.GREEN}{next_walk.due_date}{Style.RESET_ALL}")
show_pet_tasks(biscuit)

feeding = biscuit.tasks[1]
print(f"\n  {Fore.YELLOW}Completing '{feeding.title}' (ONCE) for {biscuit.name}...{Style.RESET_ALL}")
result = scheduler.mark_task_complete(biscuit, feeding)
print(f"  No recurrence — mark_task_complete returned: {Fore.RED}{result}{Style.RESET_ALL}")
show_pet_tasks(biscuit)

grooming = whiskers.tasks[1]
print(f"\n  {Fore.YELLOW}Completing '{grooming.title}' (WEEKLY) for {whiskers.name}...{Style.RESET_ALL}")
next_groom = scheduler.mark_task_complete(whiskers, grooming)
print(f"  timedelta: 7 days  →  next due_date = {Fore.GREEN}{next_groom.due_date}{Style.RESET_ALL}")
show_pet_tasks(whiskers)

# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

sam   = Owner(name="Sam", available_minutes=180, day_start=480)
buddy = Pet(name="Buddy", species="Dog",  breed="Beagle",  age=4)
luna  = Pet(name="Luna",  species="Cat",  breed="Siamese", age=2)
sam.add_pet(buddy)
sam.add_pet(luna)

buddy.add_task(Task("Vet Check",    "Annual checkup",        30, Priority.HIGH,   due_time=570))
luna.add_task( Task("Bath Time",    "Full wash and dry",     20, Priority.HIGH,   due_time=560))
buddy.add_task(Task("Evening Walk", "Long walk at the park", 30, Priority.MEDIUM, due_time=1080))

conflict_scheduler = Scheduler(owner=sam)
conflict_tasks = conflict_scheduler.collect_all_tasks()

section("Conflict Detection")

window_rows = [
    [
        f"{species_icon(p.species)} {p.name}",
        t.title,
        f"{_fmt(t.due_time - t.duration_minutes)} – {_fmt(t.due_time)}",
        priority_label(t.priority),
    ]
    for p, t in conflict_tasks
]
print(tabulate(window_rows, headers=["Pet", "Task", "Ideal window", "Priority"], tablefmt="rounded_outline"))

print()
warnings = conflict_scheduler.detect_conflicts(conflict_tasks)
if warnings:
    for w in warnings:
        print(Fore.RED + Style.BRIGHT + "  ⚠️  " + w + Style.RESET_ALL)
else:
    print(Fore.GREEN + "  ✅ No conflicts detected." + Style.RESET_ALL)
