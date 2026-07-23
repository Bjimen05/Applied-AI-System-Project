import logging

import streamlit as st
from pawpal_system import Frequency, Owner, Pet, Priority, Scheduler, Task, load_from_json
from evaluator import Evaluator, Severity, safe_save_plan
from retriever import Document, Retriever
from specialized_model import TaskClassifier, UrgencyTier
from agent import PawPalAgent

logging.basicConfig(
    filename="pawpal.log", level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

if "custom_notes" not in st.session_state:
    st.session_state.custom_notes = []

retriever = Retriever()
retriever.add_documents(st.session_state.custom_notes)
classifier = TaskClassifier(retriever=retriever)

TIER_ICON = {
    UrgencyTier.ROUTINE: "🟢",
    UrgencyTier.SOON: "🟡",
    UrgencyTier.URGENT: "🟠",
    UrgencyTier.CRITICAL: "🔴",
}

SPECIES_ICON = {"dog": "🐕", "cat": "🐈", "rabbit": "🐇"}

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

st.markdown("""
<style>
    div[data-testid="stMetric"] {
        background-color: #FFF3E0;
        border-radius: 10px;
        padding: 12px 16px;
    }
    div[data-testid="stForm"] {
        border-radius: 12px;
    }
    .pawpal-tagline {
        color: #6D4C41;
        font-size: 1.05rem;
        margin-top: -8px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🐾 PawPal+")
st.markdown(
    '<p class="pawpal-tagline">AI-augmented daily care planning — scheduling, retrieval, '
    "urgency scoring, and reliability guardrails working together.</p>",
    unsafe_allow_html=True,
)

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


def species_icon(species: str) -> str:
    return SPECIES_ICON.get(species.lower(), "🐾")


# ---------------------------------------------------------------------------
# Sidebar — owner info + add a pet
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("🐾 Owner & Pet Setup")

    with st.form("owner_form"):
        owner_name = st.text_input("Owner name", value="Jordan")
        available_minutes = st.number_input("Available minutes today", min_value=10, max_value=480, value=120)
        day_start_hour = st.number_input("Day start hour (24h)", min_value=4, max_value=12, value=8)

        st.markdown("**Add / select a pet**")
        pet_name = st.text_input("Pet name", value="Mochi")
        species = st.selectbox("Species", ["dog", "cat", "rabbit", "other"])
        breed = st.text_input("Breed", value="Mixed")
        age = st.number_input("Age", min_value=0, max_value=30, value=2)

        submitted = st.form_submit_button("Save", width='stretch')

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

    if st.session_state.owner is not None:
        st.divider()
        st.caption("Current household")
        c1, c2 = st.columns(2)
        c1.metric("Budget", f"{st.session_state.owner.available_minutes} min")
        c2.metric("Day starts", fmt_time(st.session_state.owner.day_start))
        st.metric("Pets", len(st.session_state.owner.list_pets()))

# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

if st.session_state.owner is None or st.session_state.active_pet is None:
    st.info("👋 Set an owner and pet in the sidebar to get started.")
else:
    owner = st.session_state.owner
    scheduler = Scheduler(owner=owner)
    all_pairs = scheduler.collect_all_tasks()

    # -------------------------------------------------------------------
    # Pet cards — one per pet, click to make active
    # -------------------------------------------------------------------
    st.subheader("Your Pets")
    pet_cols = st.columns(len(owner.list_pets()))
    for col, pet in zip(pet_cols, owner.list_pets()):
        pending_count = len(scheduler.filter_tasks(all_pairs, completed=False, pet_name=pet.name))
        is_active = pet.name == st.session_state.active_pet.name
        with col:
            with st.container(border=True):
                st.markdown(f"### {species_icon(pet.species)} {pet.name}")
                st.caption(f"{pet.breed} · {pet.species} · age {pet.age}")
                st.markdown(f"**{pending_count}** pending task(s)")
                if is_active:
                    st.success("✅ Active")
                else:
                    if st.button("Select", key=f"select_{pet.name}", width='stretch'):
                        st.session_state.active_pet = pet
                        st.rerun()

    st.divider()

    # -------------------------------------------------------------------
    # Tasks tab — add + view + RAG + model insight for the active pet
    # -------------------------------------------------------------------
    tab_tasks, tab_schedule = st.tabs(["📋 Tasks", "🤖 Build Schedule"])

    with tab_tasks:
        with st.container(border=True):
            st.markdown(f"#### Add a Task for **{st.session_state.active_pet.name}**")
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

            if st.button("➕ Add task", width='stretch'):
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

        st.markdown(f"#### Tasks for **{st.session_state.active_pet.name}**")

        pet_pending = scheduler.filter_tasks(
            all_pairs, completed=False, pet_name=st.session_state.active_pet.name,
        )
        sorted_pending = scheduler.sort_by_time(pet_pending)

        if sorted_pending:
            st.dataframe(
                [
                    {
                        "Title": t.title,
                        "Duration (min)": t.duration_minutes,
                        "Priority": t.priority.name,
                        "Due by": fmt_time(t.due_time),
                        "Repeats": t.frequency.value,
                    }
                    for _, t in sorted_pending
                ],
                width='stretch', hide_index=True,
            )

            conflicts = scheduler.detect_conflicts(pet_pending)
            if conflicts:
                st.markdown("**Scheduling conflicts detected:**")
                for warning in conflicts:
                    st.warning(warning)
            else:
                st.success("No scheduling conflicts.")

            care_tab, model_tab, notes_tab = st.tabs(
                ["📚 Care Tips (RAG)", "🎯 Urgency (Model)", "📝 Custom Notes"],
            )

            with care_tab:
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

            with model_tab:
                for _, t in sorted_pending:
                    assessment = classifier.classify(t, st.session_state.active_pet, owner.day_start)
                    icon = TIER_ICON[assessment.urgency_tier]
                    st.markdown(f"{icon} **{t.title}** — {assessment.rationale}")

            with notes_tab:
                note_text = st.text_input(
                    f"Add a custom care note for {st.session_state.active_pet.name}",
                    key="custom_note_input",
                    placeholder="e.g. Buddy is allergic to chicken, use turkey-based kibble",
                )
                if st.button("Add note") and note_text.strip():
                    doc = Document(
                        doc_id=f"custom-{st.session_state.active_pet.name}-{len(st.session_state.custom_notes)}",
                        species=st.session_state.active_pet.species,
                        category="general",
                        text=note_text.strip(),
                    )
                    st.session_state.custom_notes.append(doc)
                    st.success("Note added — it'll be included in future care tips for this species.")
                    st.rerun()
        else:
            st.info("No pending tasks yet — add one above.")

    # -------------------------------------------------------------------
    # Schedule tab — agent-orchestrated build + reliability review
    # -------------------------------------------------------------------
    with tab_schedule:
        if st.button("🤖 Run Agent & Build Schedule", type="primary", width='stretch'):
            agent = PawPalAgent(owner, retriever=retriever, classifier=classifier)
            st.session_state.agent_result = agent.run(
                human_reviewed=st.session_state.reviewed_risky_plan,
                save_path="data.json",
            )

        if st.session_state.get("agent_result") is not None:
            result = st.session_state.agent_result
            plan = result.plan

            with st.container(border=True):
                st.markdown("#### 🤖 Agent actions")
                for a in result.actions_taken:
                    st.caption(f"• {a}")

            st.markdown("#### Today's Plan")

            if plan.entries:
                m1, m2, m3 = st.columns(3)
                m1.metric("Scheduled", len(plan.entries))
                m2.metric("Minutes used", f"{plan.total_time_used()} / {owner.available_minutes}")
                m3.metric("Skipped", len(plan.skipped_tasks))

                st.dataframe(
                    [
                        {
                            "Time slot": f"{fmt_time(e.start_time)} – {fmt_time(e.end_time)}",
                            "Pet": e.pet.name,
                            "Task": e.task.title,
                            "Priority": e.task.priority.name,
                            "Duration (min)": e.task.duration_minutes,
                            "Repeats": e.task.frequency.value,
                        }
                        for e in plan.entries
                    ],
                    width='stretch', hide_index=True,
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
                        msg = f"**{task.title}** ({pet.name}) — skipped because the time budget is full."
                    st.warning(msg)

            with st.expander("Why was this plan chosen?"):
                st.text(plan.explain())

            st.markdown("#### 🛡️ Plan Review")
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
                if st.button("💾 Re-run Agent & Save", disabled=save_disabled, width='stretch'):
                    agent = PawPalAgent(owner, retriever=retriever, classifier=classifier)
                    st.session_state.agent_result = agent.run(
                        human_reviewed=st.session_state.reviewed_risky_plan,
                        save_path="data.json",
                    )
                    st.session_state.reviewed_risky_plan = False
                    st.rerun()
