# Model Card / Responsible-AI Reflection — PawPal+

## Limitations and Biases

- The knowledge base is 18 hand-written documents covering dog/cat/rabbit only. Any other pet gets generic "any"-tagged advice at best — coverage is narrow and reflects my own assumptions about common pets, not a validated source.
- Retrieval is keyword/Jaccard overlap, not semantic understanding. A care tip phrased with different words than the KB (a synonym, a typo, a rephrasing) can simply return nothing, and the system won't know it missed something.
- The "specialized model" is a hand-tuned scoring formula (fixed point values for priority, deadline pressure, overdue status, risk), not learned from real data. The weights are my own guesses at what matters, not validated against how actual pet owners judge urgency.
- The high-risk detector can both under-flag (a risky task phrased in unexpected words) and over-flag (a benign task that happens to share vocabulary with a medical KB entry) — it's a heuristic, not a medical judgment.

## Could This Be Misused?

The biggest risk is false confidence: the "urgency score" and care tips look authoritative but are not real veterinary advice, just fixed text I wrote. An owner could over-trust a medication-related schedule because the system "reviewed" it, when the review is a keyword/retrieval heuristic, not clinical judgment.

The human-review gate is also just a boolean (`human_reviewed=True`) passed by the caller — nothing authenticates that a human actually looked at anything. Any code calling `safe_save_plan` (or bypassing it and calling `save_to_json` directly) can set that flag to `True` without real review.

**How I'd prevent it:** keep the disclaimer explicit that this is not medical advice, never let the model's urgency score auto-approve a health-related task (already enforced — high-risk findings always require the review flag), and if this went further than a class project, replace the boolean flag with an actual authenticated approval step (e.g., a logged user action) instead of a trusted parameter.

## What Surprised Me About Reliability

The retriever's plural-matching bug (`"walks"` vs `"walk"`) passed every automated test, because my test fixtures happened to use words that matched the KB exactly. It only showed up when I ran the CLI with real task descriptions. That was the biggest surprise: 100% passing tests didn't mean the feature actually worked end-to-end — my tests were unintentionally shaped by the same assumptions as my implementation.

I was also surprised how a cross-component gap opened up that neither piece had alone: the Scheduler was correct, the Evaluator's original `priority_inversion` check was correct for what it checked, but neither caught a MEDIUM overdue task losing to a HIGH task with no time pressure — that only became visible once the specialized model's continuous score existed to compare against.

## Collaboration With AI

I worked with Claude iteratively: I set the scope and constraints (offline-only, no API key, must integrate into the working app, not sit as a demo), and Claude implemented each layer, wrote its own tests, and ran them before I saw results.

**Helpful suggestion:** When building the agent's repair loop, Claude reused the same scoring logic already written for the Evaluator's `model_priority_mismatch` check instead of writing a second, parallel version — keeping the "what counts as a mismatch" rule in exactly one place so the two components can't quietly disagree.

**Flawed suggestion:** Claude's first test scenario for the agent's repair loop assumed a task due shortly after the day start would get skipped for running out of *budget*. It actually failed for a different reason — it physically couldn't finish before its own deadline (a "deadline skip," not a "budget skip"), so promoting its priority didn't change anything and the test failed. Claude had to debug why, then redesign the task's due time so the skip was really budget-driven. It was a useful mistake — it exposed that "priority mismatch" and "infeasible deadline" are different problems, and promoting priority only fixes the first one.
