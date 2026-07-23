# Model Card / Responsible-AI Reflection — PawPal+

## Limitations and Biases

- The knowledge base is 18 hand-written documents covering dog/cat/rabbit only. Any other pet gets generic "any"-tagged advice at best — coverage is narrow and reflects my own assumptions about common pets, not a validated source.
- Retrieval is keyword/Jaccard overlap, not semantic understanding. A care tip phrased with different words than the KB (a synonym, a typo, a rephrasing) can simply return nothing, and the system won't know it missed something.
- The "specialized model" is a hand-tuned scoring formula (fixed point values for priority, deadline pressure, overdue status, risk), not learned from real data. The weights are my own guesses at what matters, not validated against how actual pet owners judge urgency.
- The high-risk detector can both under-flag (a risky task phrased in unexpected words) and over-flag (a benign task that happens to share vocabulary with a medical KB entry) — it's a heuristic, not a medical judgment.

**Future improvements I'd prioritize:** replace Jaccard/keyword retrieval with real embeddings so paraphrases and synonyms actually match instead of silently returning nothing; replace the hand-tuned scoring weights with values fit against real labeled examples (even a small survey of pet owners ranking task urgency) instead of my own guesses; and turn `human_reviewed` into an authenticated, logged approval action instead of a trusted boolean, closing the misuse gap described below.

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

## Specialized Model vs. Baseline (Stretch: Fine-Tuning/Specialization)

`specialization_eval.py` runs a synthetic set of 10 tasks through two things: a naive **baseline** that maps declared `Priority` straight to an urgency label (HIGH→critical, MEDIUM→soon, LOW→routine, ignoring everything else), and the specialized `TaskClassifier`, which blends priority with deadline pressure, overdue status, and RAG-flagged risk into a continuous 0–100 score. Real output from running the script:

| Task | Priority | Baseline | Specialized | Score | Agreement |
|---|---|---|---|---|---|
| Feeding | HIGH | critical | critical | 99/100 | match |
| Grooming (overdue) | MEDIUM | soon | urgent | 82/100 | **DIFFERS** |
| Enrichment | LOW | routine | routine | 20/100 | match |
| Afternoon walk | MEDIUM | soon | urgent | 68/100 | **DIFFERS** |
| Evening walk | HIGH | critical | urgent | 70/100 | **DIFFERS** |
| Vet Check | MEDIUM | soon | urgent | 76/100 | **DIFFERS** |
| Litter box (overdue) | LOW | routine | soon | 57/100 | **DIFFERS** |
| Insulin dose | HIGH | critical | critical | 100/100 | match |
| Brushing | MEDIUM | soon | urgent | 68/100 | **DIFFERS** |
| Nail trim | LOW | routine | soon | 43/100 | **DIFFERS** |

**Agreement: 3/10 (30%).** The disagreements are the specialized model correcting two specific blind spots the baseline can't see at all:

- **"Evening walk" (HIGH, due in 12 hours):** the baseline calls every HIGH task "critical" regardless of timing. The specialized model recognizes 12 hours of slack means it isn't actually urgent yet (70/100, "urgent" not "critical") — a measurable, deliberate *downgrade* from the naive baseline, not just an upgrade.
- **"Litter box (overdue)" (LOW, 2 days overdue) and "Grooming (overdue)" (MEDIUM, 3 days overdue):** the baseline never elevates a LOW or MEDIUM task no matter how overdue it is. The specialized model adds an overdue bonus, correctly promoting both above where a static priority label would leave them (57/100 and 82/100 respectively).

This is the same scoring logic the Evaluator's `model_priority_mismatch` check and the Agent's repair loop already depend on — it isn't a one-off demo number, it's the same behavior that changes which tasks get scheduled (see `ai_interactions.md`'s Priya scenario).

## Multi-Source RAG: Before/After (Stretch: RAG Enhancement)

`retriever.py` originally had one source: an 18-document hand-written KB. It now merges that with a second source, `data/breed_facts.json`, and supports a third — runtime custom documents an owner adds themselves (`Retriever.add_documents()`, wired into `app.py`'s "Add a custom care note" field). Real before/after output:

**Before (KB-only source) — query: "Golden Retriever exercise needs more than a short walk"**
```
dog-exercise-1  score=0.15  "Dogs generally need 30 to 60 minutes of physical exercise daily..."
```

**After (KB + breed_facts.json merged by default)** — the same query now surfaces the breed-specific passage instead, because it scores higher:
```
breed-golden-retriever-1  score=0.182  "Golden Retrievers are a high-energy sporting breed and often need close..."
```

**Custom document, added at runtime — query: "Buddy allergic to chicken kibble"**
```
Before add_documents(): breed-beagle-1  score=0.05  "Beagles are a breed especially prone to overeating..." (generic, unrelated to Buddy specifically)
After add_documents():  custom-buddy-1  score=0.5   "Buddy is allergic to chicken, use turkey-based kibble instead"
```

The custom note didn't exist anywhere until the owner typed it in, and immediately became the top-ranked result for that pet's future care tips — retrieval quality for *this specific pet* improved in a way no static KB could, without touching any other pet's results.
