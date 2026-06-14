# AI Interaction Log

A faithful, enhanced record of how this project was built with an AI pair (Claude, via Claude Code).
It is **living** — appended as the build progresses. Each entry captures the *prompt* I issued, a
*summary* of what came back, and the *correction or redirection* I made when the AI's instinct was
wrong or incomplete. The prompts here are lightly edited for readability, but the decisions,
corrections, and sequence are real.

This log is written to be useful, not performative: it shows where AI accelerated me, and — just as
importantly — where it needed steering and where I verified its output by hand.

**Prompting techniques referenced** (per Anthropic's prompting best practices and Schulhoff's
"examples > descriptions" guidance): `[clear+motivation]` state the goal and *why*; `[options]` force
2–3 alternatives with trade-offs; `[example-shape]` show the output format instead of describing it;
`[structure]` constrain output to a schema/tags; `[verify]` make the model check or refute its own
work; `[parallel]` run independent work concurrently.

---

## Phase 0 — Framing

### 0.1 — Kickoff
**My prompt** `[clear+motivation]`: "Build a vertical slice of a fleet telemetry monitoring service
(50 vehicles @ 1 Hz). The ADR and an AI-interaction log are weighted as much as the code, and the
real point is to show how I use AI to be *productive*. Start with the ADR — make it a solid, well
designed design document. Use Context7 to fetch a strong ADR template (MADR primer) so we don't wing
the structure."

**AI output (summary):** Fetched the MADR template (Context → Decision Drivers → Considered Options →
Decision Outcome → Consequences, plus status metadata, Confirmation, Pros/Cons, More Information).
Proposed driving the whole design through that structure before any code.

**My redirection:** Good — but I made clear the ADR must carry **alternatives considered and why
rejected** for *every* decision, not just the chosen path. That requirement shaped the rest.

---

## Phase 1 — Design decisions (I owned every fork)

### 1.1 — Forcing the load-bearing choices into the open
**My prompt** `[options]`: "Before writing anything, give me the 3–4 decisions that actually reshape
this system, each as a 2–3 option choice with trade-offs and your recommendation. I'll decide. Don't
bury a default."

**AI output (summary):** Surfaced four forks — persistence (Postgres vs SQLite), ADR shape, anomaly
detection scope, and live-update transport — each with a recommendation.

**My decisions / corrections:**
- **Persistence → PostgreSQL, not SQLite.** The AI's runnability instinct leaned toward SQLite
  (zero-setup). I overrode it: SQLite's single-writer model makes the zone counter *trivially*
  correct and thereby **dodges the exact concurrency question the exercise is testing**. I want real
  row-level locks, `FOR UPDATE`, and MVCC on display. Postgres in `docker-compose` is still
  one-command. *(This is the single most important correction in the project.)*
- **Anomaly detection → hybrid**, not threshold-only: instantaneous thresholds **plus** stateful
  diffs (drain rate, impossible teleport) **plus** a background staleness sweep. A silent vehicle is
  the dangerous one; pure thresholds can't see absence.
- **Transport → polling.** WebSockets are overkill for read-only 1 Hz data.
- **ADR → one consolidated, MADR-influenced document.**

### 1.2 — Architecture conventions (a hard redirection)
**My prompt** `[clear+motivation]`: "The default 'controllers/services/repositories' layering is
exactly what I *don't* want. Backend = **Vertical Slice Architecture** (organize by request, minimize
cross-slice coupling). Frontend = **Feature-Sliced Design** + **atomic design**, **shadcn**, **zod**
at the boundary, **Playwright** e2e. **Scalar** for API docs. Clean code, DRY, YAGNI, SOLID where it
earns its keep, and **do not over-comment** — comment only non-obvious intent."

**AI output (summary):** Re-grounded via Context7 on Bogard's vertical slices and the FSD layer
model (`app → pages → widgets → entities → shared`, lower-only imports, `ui/model/api/lib` segments),
then mapped atomic design onto FSD (shadcn primitives = atoms in `shared/ui`, widgets = organisms).

**My correction:** I caught one tension and forced a decision: a vertical-slice purist would
*duplicate* the fault-handling logic between the status endpoint and the telemetry path. I directed
that the fault invariant have **exactly one implementation**, with the telemetry slice delegating to
it — DRY wins over slice purity for a critical invariant, and that trade-off must be documented, not
hidden.

---

## Phase 2 — Authoring the ADR & design docs

### 2.1 — Drafting
**My prompt** `[example-shape]`: "Write the ADR and the supporting docs (architecture, a concurrency
deep-dive, and Mermaid diagrams for the system context, the ER model, and the ingest / fault /
zone-counter flows). For each decision: alternatives + why rejected + consequences. The concurrency
doc must show the *naive wrong* approach next to ours, with the SQL and the isolation level."

**AI output (summary):** Produced the consolidated ADR (8 decisions, the four required questions, a
per-operation isolation table), `architecture.md`, `concurrency-and-isolation.md`, and five Mermaid
diagrams. The isolation reasoning was specific (atomic `UPDATE … +1`, `SELECT … FOR UPDATE`
idempotency, MVCC `GROUP BY`).

**My correction:** It initially wrote present-tense ("the stack runs with one command") as if the
code already existed. I had it mark the docs as **design-phase / acceptance-criteria** so a reviewer
doesn't mistake intent for shipped code.

---

## Phase 3 — Adversarial review (don't trust the first draft)

### 3.1 — Multi-lens review
**My prompt** `[verify] [parallel] [structure]`: "Before I read the ADR, harden it. Run independent
reviewers in parallel — a concurrency engineer whose job is to **refute** the locking claims, a MADR
completeness critic, a spec-coverage auditor, a cross-file consistency checker, and a Mermaid/links
validator. Return findings as structured JSON with severity and a suggested fix. I want the locking
claims attacked, not admired."

**AI output (summary):** Five agents, 30 findings (1 critical, 9 major, 11 minor, 9 nit). The
concurrency skeptic **could not refute** the four headline guarantees (verified the
`UPDATE … +1` lost-update safety via Postgres's EvalPlanQual re-evaluation, the `FOR UPDATE`
idempotency, the MVCC aggregate, and the `ON CONFLICT … WHERE newer` guard). It surfaced real gaps:
the `FOR UPDATE` serialization assumed the vehicle row already exists; `overspeed (3.0)` contradicted
`position_jump (5.0)`; event anomalies risked unbounded duplicate rows; and the ADR linked to an
AI-log doc that didn't exist yet.

**My correction / direction:** I accepted the findings and had every real one fixed — state the
seeding precondition for the lock, reconcile the thresholds as *policy* vs *physical-impossibility*
limits, make anomaly persistence **edge-triggered**, fix a `excluded.timestamp` column bug,
standardize the `ts` name, bound offline-detection latency (~15 s), add a proper API contract, and
create the missing AI-driven-SDLC doc. The nits I judged cosmetic I noted and moved on.

### 3.2 — On the AI log itself
**My prompt** `[clear+motivation]`: "The AI log is a graded deliverable. Don't dump raw transcript —
*enhance* each interaction: show the prompt, the gist of the output, and where I corrected you, and
end with an honest reflection. Make it read like the engineering record it is."

**AI output (summary):** This document.

---

## Interim reflection (to be finalized at the end of the build)

- **Where AI was strong:** breadth and speed — fetching and synthesizing the MADR / vertical-slice /
  FSD patterns, drafting a structurally complete ADR with alternatives-and-rejections, and
  generating internally-consistent docs + diagrams in one pass. The *parallel adversarial review*
  was the standout: cheap to run, and it caught precision gaps a single pass would have shipped.
- **Where it needed steering:** it defaulted toward the *easy* answer (SQLite) over the *instructive*
  one (Postgres), and toward conventional layering over the vertical-slice/FSD structures I wanted.
  Left alone it also slid into present-tense "it works" phrasing before any code existed. These are
  judgment and framing calls — exactly where the human has to hold the line.
- **What I verified by hand:** the concurrency claims (I sanity-checked the lost-update and
  `FOR UPDATE`-idempotency reasoning against how Postgres actually behaves, rather than taking the
  draft's word), the threshold reconciliation, and that every "alternatives + why rejected" block was
  genuinely present.
- **Net:** AI compressed roughly a day of design-and-documentation into a focused session, but the
  quality came from *directing* it, *forcing* alternatives into the open, and *adversarially
  verifying* the result — not from accepting the first draft.

*(Reflection will be completed once implementation, the Playwright verification loop, and the final
review are done.)*
