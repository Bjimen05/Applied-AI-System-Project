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

*Yes, the design changed once I started implementing. My initial `Scheduler` only sorted by priority, but I realized that two high-priority tasks of very different durations could lead to an unrealistic plan (e.g., a 5-minute feeding and a 60-minute walk both marked high, leaving no room for medium tasks). I added a secondary sort by duration (shorter tasks first among equal priorities) so that the scheduler fits more tasks into the available window before time runs out. This made the output more useful without requiring a new class — just a change to the sort key inside `generate_plan()`.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
