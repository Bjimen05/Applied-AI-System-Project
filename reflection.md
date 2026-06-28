# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

*My initial UML design centered on four classes: `Owner`, `Pet`, `Task`, and `Scheduler`.

- `Owner` holds the owner's name and the total minutes available in a day. It acts as the source of the time constraint that the scheduler must respect.
- `Pet` holds the pet's name and species. It is associated with an `Owner` and serves as the context for generating a named daily plan.
- `Task` represents one care activity. It stores a title, duration in minutes, and a priority level (high / medium / low). Priority drives sort order; duration drives how quickly the daily time budget is consumed.
- `Scheduler` takes an `Owner`, a `Pet`, and a list of `Task` objects. Its `generate_plan()` method sorts tasks by priority (high first), then greedily adds tasks until the owner's available time is exhausted. It returns a list of `(start_time, Task)` tuples that form the daily plan.

I kept the design flat — no inheritance, no abstract base classes — because the scenario called for straightforward scheduling, not a plugin architecture.

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

Yes, the design changed in several ways after reviewing the skeleton for logic gaps and silent bugs:

1. **`priority: str` → `Priority` Enum.** The initial design stored priority as a plain string. During review I realized a typo like `"hihg"` would pass silently and break `priority_rank()` with no error message. Replacing it with a Python `Enum` (`HIGH=1`, `MEDIUM=2`, `LOW=3`) means invalid values raise an error at assignment, and `priority_rank()` becomes a one-liner: `return self.priority.value`.

2. **Times stored as `int` (minutes since midnight) instead of `str`.** The initial design used strings like `"08:00"` for `day_start`, `due_time`, `start_time`, and `end_time`. Computing `end_time = start_time + duration_minutes` would have required parsing and reformatting strings every time. Switching to integers (e.g. `480` = 08:00) makes the arithmetic direct and only requires formatting at display time.

3. **`remove_task(title: str)` → `remove_task(task: Task)`.** Removing a task by its title string is ambiguous if a pet has two tasks with the same name (e.g., two "Feeding" entries). Removing by object reference eliminates that ambiguity entirely.

4. **`due_time` wired into `_sort_tasks`.** The initial skeleton defined `due_time` on `Task` but never used it in scheduling. I added it as the secondary sort key (after priority, before duration) so tasks with earlier deadlines are scheduled first within the same priority tier.

5. **`date: str` added to `DailyPlan`.** The original plan had no date field, making it impossible to distinguish a Monday plan from a Tuesday one. Adding `date` costs nothing now and prevents a structural gap if recurring or multi-day scheduling is added later.

6. **`ScheduledEntry` and `DailyPlan` split into separate classes.** My initial design returned raw `(start_time, Task)` tuples from `generate_plan()`. Formalizing these as `ScheduledEntry` (with `pet`, `task`, `start_time`, `end_time`) and `DailyPlan` (with `entries`, `skipped_tasks`, `explain()`) makes the output structured and gives the UI a clean interface to display both what was scheduled and what was skipped and why.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

*The scheduler uses four constraints: available time, priority (HIGH/MEDIUM/LOW), due time, and duration. It also boosts urgency for tasks due within 60 minutes. Priority comes first for importance, then due time, then duration as a tiebreaker, while available time limits the schedule.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

*The scheduler uses a greedy algorithm, sorting tasks by priority and filling time step by step. It’s fast and simple, but not always optimal since some time may be wasted. More advanced methods could schedule more efficiently, but this approach keeps important tasks prioritized and easy to understand.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

*I use Ai tools for design, brainstroming, debugging  refactoring. Designing and brainstorming the UML diagram, debugging specifically the pawpal_system.py for the correct logic, refactoring my entire code to be more professional and correct.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

*The AI suggest to remove the comments for the code and I did not accept that by finding what it wants to delete.
---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

*I tested many behaviors with task like if a task is correctly marked as completed, stored correctly in a pet's task list, recurring tasks, sorting and filtering tasks. As well as conflict detection, schedule generation, skipped task handling, priority & urgency logic and total scheduling time.

These test were important because it verify that the core features work correctly and handle both normal and edge cases, as to help catch bugs very early.

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

*I'm very confident that my scheduler work correctly. I will test edge cases like tasks already past due before the day start, three overlapping tasks instead of two, making sure the remove methods work correctly, midnigt tasks are handled correctly, pets with no tasks don't cause errors. 

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

*Designing the UML diagram and writing the algorithm methods because it allows me to critically think what classes and methods I need.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

*I would improve the scheduling algorithm to better optimize available time, add support for task editing and deletion in the UI, improve conflict detection for more complex overlaps, add more input validation and edge-case tests.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

*That it takes time to design and brainstorm on how to make a project, that there is more than just coding, I need to plan what I need for my project instead just coding straight away, as  well as reviewing what the AI suggests so it correctly add based on what I planned.