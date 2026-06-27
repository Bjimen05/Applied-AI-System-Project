import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler, Priority

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

# ---------------------------------------------------------------------------
# Session state vault — initialize objects once, persist across reruns
# ---------------------------------------------------------------------------

# Owner: created when the user clicks "Set Owner", updated if they click again
if "owner" not in st.session_state:
    st.session_state.owner = None

# Active pet: the pet currently selected for adding tasks
if "active_pet" not in st.session_state:
    st.session_state.active_pet = None

# ---------------------------------------------------------------------------
# Owner + pet setup
# ---------------------------------------------------------------------------

with st.form("owner_form"):
    col1, col2 = st.columns(2)
    with col1:
        owner_name = st.text_input("Owner name", value="Jordan")
        available_minutes = st.number_input("Available minutes today", min_value=10, max_value=480, value=120)
        day_start_hour = st.number_input("Day start hour (24h)", min_value=4, max_value=12, value=8)
    with col2:
        pet_name = st.text_input("Pet name", value="Mochi")
        species = st.selectbox("Species", ["dog", "cat", "rabbit", "other"])
        breed = st.text_input("Breed", value="Mixed")
        age = st.number_input("Age", min_value=0, max_value=30, value=2)
    submitted = st.form_submit_button("Set Owner & Pet")

if submitted:
    day_start = int(day_start_hour) * 60
    # Preserve existing owner and pets if only the name matches; otherwise start fresh
    existing = st.session_state.owner
    if existing is None or existing.name != owner_name:
        st.session_state.owner = Owner(
            name=owner_name,
            available_minutes=int(available_minutes),
            day_start=day_start,
        )
    else:
        # Update mutable settings without wiping pets
        existing.available_minutes = int(available_minutes)
        existing.day_start = day_start

    # Only create a new Pet if one with this name doesn't already exist on the owner
    existing_names = [p.name for p in st.session_state.owner.list_pets()]
    if pet_name not in existing_names:
        pet = Pet(name=pet_name, species=species, breed=breed, age=int(age))
        st.session_state.owner.add_pet(pet)
        st.session_state.active_pet = pet
    else:
        # Re-select the pet by name so active_pet stays in sync
        st.session_state.active_pet = next(
            p for p in st.session_state.owner.list_pets() if p.name == pet_name
        )
    st.success(f"Owner '{owner_name}' set with pet '{pet_name}'.")

# ---------------------------------------------------------------------------
# Task form — only shown once an owner + pet exist
# ---------------------------------------------------------------------------

st.markdown("### Tasks")

if st.session_state.owner is None or st.session_state.active_pet is None:
    st.info("Set an owner and pet above before adding tasks.")
else:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    with col3:
        priority = st.selectbox("Priority", ["HIGH", "MEDIUM", "LOW"], index=0)
    with col4:
        due_hour = st.number_input("Due by (hour, 24h)", min_value=0, max_value=23, value=9)

    if st.button("Add task"):
        task = Task(
            title=task_title,
            description="",
            duration_minutes=int(duration),
            priority=Priority[priority],
            due_time=int(due_hour) * 60,
        )
        st.session_state.active_pet.add_task(task)
        st.success(f"Added '{task_title}' to {st.session_state.active_pet.name}.")

    pending = st.session_state.active_pet.get_pending_tasks()
    if pending:
        st.write(f"Tasks for **{st.session_state.active_pet.name}**:")
        st.table([
            {"title": t.title, "duration_minutes": t.duration_minutes, "priority": t.priority.name}
            for t in pending
        ])
    else:
        st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")

if st.button("Generate schedule"):
    if st.session_state.owner is None:
        st.warning("Set an owner and pet first.")
    else:
        scheduler = Scheduler(owner=st.session_state.owner)
        plan = scheduler.generate_plan()

        st.markdown("#### Today's Plan")
        st.text(plan.display())

        with st.expander("Why was this plan chosen?"):
            st.text(plan.explain())
