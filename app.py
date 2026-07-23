import streamlit as st
from pawpal_system import Frequency, Owner, Pet, Priority, Scheduler, Task, load_from_json
from evaluator import Evaluator, Severity, safe_save_plan
from retriever import Retriever
from specialized_model import TaskClassifier, UrgencyTier
from agent import PawPalAgent

retriever = Retriever()
classifier = TaskClassifier(retriever=retriever)

TIER_ICON = {
    UrgencyTier.ROUTINE: "🟢",
    UrgencyTier.SOON: "🟡",
    UrgencyTier.URGENT: "🟠",
    UrgencyTier.CRITICAL: "🔴",
}

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

# ---------------------------------------------------------------------------
# Session state — initialize once, persist across reruns
# ---------------------------------------------------------------------------

if "owner" not in st.session_state:
    try:
        st.session_state.owner = load_from_json()
    except FileNotFoundError:
        st.session_state.owner = None

if "active_pet" not in st.session_state:
    st.session_state.active_pet = (
        st.session_state.owner.list_pets()[0] if st.session_state.owner and st.session_state.owner.list_pets() else None
    )

if "reviewed_risky_plan" not in st.session_state:
    st.session_state.reviewed_risky_plan = False

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def fmt_time(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"

# ---------------------------------------------------------------------------
# Owner + pet setup
# ---------------------------------------------------------------------------

with st.form("owner_form"):
    col1, col2 = st.columns(2)
    with col1:
        owner_name       = st.text_input("Owner name", value="Jordan")
        available_minutes = st.number_input("Available minutes today", min_value=10, max_value=480, value=120)
        day_start_hour   = st.number_input("Day start hour (24h)", min_value=4, max_value=12, value=8)
    with col2:
        pet_name = st.text_input("Pet name", value="Mochi")
        species  = st.selectbox("Species", ["dog", "cat", "rabbit", "other"])
        breed    = st.text_input("Breed", value="Mixed")
        age      = st.number_input("Age", min_value=0, max_value=30, value=2)
    submitted = st.form_submit_button("Set Owner & Pet")

if submitted:
    day_start = int(day_start_hour) * 60
    existing = st.session_state.owner
    if existing is None or existing.name != owner_name:
        st.session_state.owner = Owner(
            name=owner_name,
            available_minutes=int(available_minutes),
            day_start=day_start,
        )
    else:
        existing.available_minutes = int(available_minutes)
        existing.day_start = day_start

    existing_names = [p.name for p in st.session_state.owner.list_pets()]
    if pet_name not in existing_names:
        pet = Pet(name=pet_name, species=species, breed=breed, age=int(age))
        st.session_state.owner.add_pet(pet)
        st.session_state.active_pet = pet
    else:
        st.session_state.active_pet = next(
            p for p in st.session_state.owner.list_pets() if p.name == pet_name
        )
    st.success(f"Owner '{owner_name}' set with pet '{pet_name}'.")

# ---------------------------------------------------------------------------
# Task form — only shown once an owner + pet exist
# ---------------------------------------------------------------------------

st.markdown("### Add a Task")

if st.session_state.owner is None or st.session_state.active_pet is None:
    st.info("Set an owner and pet above before adding tasks.")
else:
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
    with col3:
        priority = st.selectbox("Priority", ["HIGH", "MEDIUM", "LOW"], index=0)
    with col4:
        due_hour = st.number_input("Due by (hour, 24h)", min_value=0, max_value=23, value=9)
    with col5:
        frequency = st.selectbox("Repeats", ["ONCE", "DAILY", "WEEKLY"], index=0)

    if st.button("Add task"):
        task = Task(
            title=task_title,
            description="",
            duration_minutes=int(duration),
            priority=Priority[priority],
            due_time=int(due_hour) * 60,
            frequency=Frequency[frequency],
        )
        st.session_state.active_pet.add_task(task)
        st.success(f"Added '{task_title}' to {st.session_state.active_pet.name}.")

    # -----------------------------------------------------------------------
    # Pending task list — sorted by due time via Scheduler.sort_by_time
    # -----------------------------------------------------------------------

    st.markdown(f"#### Tasks for **{st.session_state.active_pet.name}**")

    scheduler = Scheduler(owner=st.session_state.owner)
    all_pairs = scheduler.collect_all_tasks()

    # Filter to this pet's pending tasks, then sort chronologically
    pet_pending = scheduler.filter_tasks(
        all_pairs,
        completed=False,
        pet_name=st.session_state.active_pet.name,
    )
    sorted_pending = scheduler.sort_by_time(pet_pending)

    if sorted_pending:
        st.table([
            {
                "Title": t.title,
                "Duration (min)": t.duration_minutes,
                "Priority": t.priority.name,
                "Due by": fmt_time(t.due_time),
                "Repeats": t.frequency.value,
            }
            for _, t in sorted_pending
        ])

        # -------------------------------------------------------------------
        # Conflict warnings — shown directly under the task list
        # -------------------------------------------------------------------
        conflicts = scheduler.detect_conflicts(pet_pending)
        if conflicts:
            st.markdown("**Scheduling conflicts detected:**")
            for warning in conflicts:
                st.warning(warning)
        else:
            st.success("No scheduling conflicts.")

        # ---------------------------------------------------------------
        # RAG — care-guide passages retrieved per pending task
        # ---------------------------------------------------------------
        with st.expander("📚 Care tips for these tasks"):
            any_hit = False
            for _, t in sorted_pending:
                hits = retriever.retrieve_for_task(
                    t.title, t.description, st.session_state.active_pet.species, top_k=1,
                )
                if hits:
                    any_hit = True
                    st.markdown(f"**{t.title}** — {hits[0].document.text}")
            if not any_hit:
                st.caption("No matching care-guide passages for these tasks yet.")

        # -----------------------------------------------------------------
        # Specialized model — structured urgency assessment per task
        # -----------------------------------------------------------------
        with st.expander("🎯 Model urgency assessment"):
            for _, t in sorted_pending:
                assessment = classifier.classify(t, st.session_state.active_pet, st.session_state.owner.day_start)
                icon = TIER_ICON[assessment.urgency_tier]
                st.markdown(f"{icon} **{t.title}** — {assessment.rationale}")
    else:
        st.info("No pending tasks yet — add one above.")

st.divider()

# ---------------------------------------------------------------------------
# Schedule generation — orchestrated by the agent
# ---------------------------------------------------------------------------

st.subheader("Build Schedule")

if st.button("🤖 Run Agent & Build Schedule"):
    if st.session_state.owner is None:
        st.warning("Set an owner and pet first.")
    else:
        agent = PawPalAgent(st.session_state.owner, retriever=retriever, classifier=classifier)
        st.session_state.agent_result = agent.run(
            human_reviewed=st.session_state.reviewed_risky_plan,
            save_path="data.json",
        )

if st.session_state.get("agent_result") is not None:
    result = st.session_state.agent_result
    plan = result.plan

    st.markdown("#### Agent actions")
    for a in result.actions_taken:
        st.caption(f"• {a}")

    st.markdown("#### Today's Plan")

    if plan.entries:
        st.table([
            {
                "Time slot": f"{fmt_time(e.start_time)} – {fmt_time(e.end_time)}",
                "Pet": e.pet.name,
                "Task": e.task.title,
                "Priority": e.task.priority.name,
                "Duration (min)": e.task.duration_minutes,
                "Repeats": e.task.frequency.value,
            }
            for e in plan.entries
        ])
        st.success(
            f"Scheduled {len(plan.entries)} task(s) — "
            f"{plan.total_time_used()} / {st.session_state.owner.available_minutes} min used."
        )
    else:
        st.info("No tasks could be scheduled.")

    if plan.skipped_tasks:
        st.markdown("**Skipped tasks:**")
        for pet, task, reason in plan.skipped_tasks:
            if reason == "deadline":
                msg = (
                    f"**{task.title}** ({pet.name}) — skipped because it would "
                    f"finish after its deadline ({fmt_time(task.due_time)})."
                )
            else:
                msg = (
                    f"**{task.title}** ({pet.name}) — skipped because "
                    f"the time budget is full."
                )
            st.warning(msg)

    with st.expander("Why was this plan chosen?"):
        st.text(plan.explain())

    # -----------------------------------------------------------------
    # Reliability layer — guardrails gate whether this plan can be saved
    # -----------------------------------------------------------------
    st.markdown("#### Plan Review")
    findings = result.findings

    if not findings:
        st.success("Evaluator: no issues found.")
    for f in findings:
        if f.severity == Severity.CRITICAL:
            st.error(f"🚫 {f.message}")
        elif f.severity == Severity.WARNING:
            st.warning(("🩺 " if f.requires_human_review else "⚠️ ") + f.message)
        else:
            st.info(f.message)

    blocked = not Evaluator.passed(findings)

    if blocked:
        st.error("This plan has a structural problem the agent couldn't fix and cannot be saved.")
    elif result.needs_human_review:
        st.session_state.reviewed_risky_plan = st.checkbox(
            "I've reviewed the flagged health/medication task(s) above and approve this plan.",
            value=st.session_state.reviewed_risky_plan,
        )
    else:
        st.session_state.reviewed_risky_plan = True

    if result.saved:
        st.success("Plan saved to data.json.")
    elif not blocked:
        save_disabled = result.needs_human_review and not st.session_state.reviewed_risky_plan
        if st.button("💾 Re-run Agent & Save", disabled=save_disabled):
            agent = PawPalAgent(st.session_state.owner, retriever=retriever, classifier=classifier)
            st.session_state.agent_result = agent.run(
                human_reviewed=st.session_state.reviewed_risky_plan,
                save_path="data.json",
            )
            st.session_state.reviewed_risky_plan = False
            st.rerun()
