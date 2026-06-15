# AI Interaction Log

This is the engineering record of how I built the fleet telemetry service with an AI pair (Claude,
via Claude Code). It is deliberately structured **task by task**: for each unit of work you get the
*prompt* I wrote, *what came back*, the **verification gate** I held the AI to before accepting the
result, and the *steering* where I overrode it. The point isn't a tool that got everything right —
it's a disciplined, human-driven process where the AI does the breadth and I own the direction, the
standards, and the gate.

Prompts are lightly edited for readability; the decisions, corrections, gates, and outcomes are
exactly as they happened.

## How I prompt (and why)

I work from Anthropic's prompt-engineering guide and Schulhoff's "examples beat descriptions"
principle. The levers I lean on, tagged throughout:

- **`[goal+why]`** — state the outcome *and the motivation*; the model generalizes far better from a
  reason ("so the grader can *see* the lock") than from a bare instruction.
- **`[force-options]`** — make it surface 2–4 real alternatives with trade-offs before committing, so
  *I* decide, not its defaults.
- **`[structure]`** — XML/section tags (`<goal>`, `<constraints>`, `<acceptance>`) so a complex ask
  parses unambiguously.
- **`[example]`** — show the exact output shape (a sample finding, a plan step, a section skeleton)
  rather than describing it; examples steer format harder than any adjective.
- **`[acceptance]`** — define "done" as a checkable, falsifiable gate up front ("don't claim done
  until `pytest` is green"), never a vibe.
- **`[critique-chain]`** — generate → have it *attack* its own work → revise, as separate steps so I
  can inspect each. "Refute the claim" is this lever pointed at correctness.
- **`[verify-in-the-real-thing]`** — for anything user-facing, the gate is the running system
  (Postgres, a browser via Playwright), not a green unit test.

## Task breakdown

| # | Task | Verification gate | Outcome |
| - | ---- | ----------------- | ------- |
| 1 | Lock in the standards (MADR, VSA, FSD, Scalar, the prompt guide) | 6 sources × 3–5 written rules before any design | Standards as explicit rules |
| 2 | Force the load-bearing decisions into the open | Each decision has a recorded rationale line | Postgres, hybrid anomalies, polling |
| 3 | Author the ADR + design docs + diagrams | Self-review: 0 placeholders; the 4 questions answerable from the ADR alone | MADR ADR, concurrency doc, diagrams |
| 4 | Adversarially review the ADR before I read it | 5 lenses; concurrency lens must *refute*; findings as JSON; re-grep clean | 30 findings, 0 guarantees refuted |
| 5 | Turn the ADR into TDD plans | Zero placeholders — every load-bearing step ships runnable code | Backend + frontend plans |
| 6 | Build the backend (raw SQL, vertical slices) | **17 tests green incl. the 2 concurrency proofs** | Concurrency-safe service |
| 7 | Build the frontend (FSD, shadcn, zod) | `tsc -b && vite build` clean | Live dashboard |
| 8 | Browser-verify loop | Named e2e assertions pass; root-cause every failure | Caught CORS, fault-not-terminal, a 500 |
| 9 | Code-smell sweep + remediation | 5-lens audit; `pytest` green after each theme | 41 findings → 8 behaviour-preserving themes |
| 10 | Flatten the rule engine + frontend UX states | 17 backend + 4 e2e green | Rule registry; skeletons/empty/error/toast |
| 11 | Data-layer debate → slice queries + verified runbook | I make it argue both sides; then *run* the doc | Stood its ground; caught a Dockerfile bug |
| 12 | Make the simulator behave like a real fleet | anomaly mix clean; full idle→moving→charging lifecycle | sticky per-vehicle state machine |

---

## Task 1 — Lock in the standards

**Prompt** `[goal+why] [acceptance]`:
> Before we write a line: this is graded as an AI-driven SDLC, and the ADR and this log count as much
> as the code — so I won't have us winging conventions. Pull the *current* canonical sources (use
> Context7 / the web, not training memory): the MADR ADR template, Bogard's Vertical Slice
> Architecture, Feature-Sliced Design, the Scalar + FastAPI integration, and Anthropic's
> prompt-engineering guide. Distil each into **3–5 numbered rules in `rule → why` form**. Do not
> proceed to design until all six sources have explicit rules.

**What came back:** all six fetched and reduced to rules, e.g. *VSA-1: a new endpoint adds a folder
under `features/`, never edits a shared `services/` layer — so unrelated features can't break each
other.* / *FSD-1: imports only point at strictly-lower layers — so a leaf change can't ripple upward.*

**Gate (falsifiable):** six sources, each with ≥3 written rules. Anything less and we don't design.

**My steering:** I added the non-negotiable that the ADR carry **alternatives + why rejected** for
every decision. That one rule shaped everything downstream.

## Task 2 — Force the load-bearing decisions into the open

**Prompt** `[force-options] [structure]`:
> `<task>`Surface the 3–4 decisions that actually reshape this system and put each to me as a 2–4
> option choice with trade-offs and your recommendation. I decide — you don't get to bury a
> default.`</task>`
> `<constraints>`Lead with the recommended option and say *why*. The graded axis is concurrency
> correctness, so weight every option by how well it lets us *demonstrate* the right isolation
> strategy, not by what's easiest to stand up.`</constraints>`

**My decisions (the ones that mattered):**
- **Postgres, not SQLite.** Its instinct leaned SQLite for zero-setup. I overrode it: SQLite's single
  writer makes the zone counter *trivially* correct and thereby **dodges the exact question being
  graded**. I want real row locks, `FOR UPDATE`, and MVCC on display. *(The single most important
  call in the project.)*
- **Hybrid anomalies** (thresholds + stateful diffs + a background staleness sweep) — a silent
  vehicle is the dangerous one, and thresholds can't see absence.
- **Polling**, not WebSockets, for a read-only 1 Hz feed.

**Gate (falsifiable):** every decision lands in the ADR with a one-line recorded rationale *before*
any code — so the ADR is written from real reasoning, not post-hoc.

## Task 3 — Author the ADR + design docs + diagrams

**Prompt** `[structure] [example] [acceptance]`:
> `<goal>`Write the ADR as a MADR-structured record, plus the supporting docs.`</goal>`
> `<per_decision_skeleton>`Fill this for every decision — no exceptions:
> ```
> ### D<n> — <decision>
> **Decision.** …
> **Alternatives considered & why rejected.** <named option> — rejected because …
> **Consequences.** Good: … Bad: … Neutral: …
> ```
> `</per_decision_skeleton>`
> `<must_include>`A concurrency deep-dive that puts the naive-wrong approach beside ours, with the
> exact SQL and isolation level. Mermaid for system context, the ER model, and the ingest / fault /
> zone-counter flows.`</must_include>`
> `<acceptance>`A reviewer can answer the four required questions (key decisions, assumptions, scale,
> omissions) from the ADR alone, and can see the locking strategy without opening the code.`</acceptance>`

**What came back:** the consolidated ADR (8 decisions in that skeleton, the four questions, a
per-operation isolation table), `architecture.md`, `concurrency-and-isolation.md`, five diagrams.

**Verification loop:** self-review pass — scanned for placeholders/TBDs, cross-checked the ER model
against the SQL, confirmed every decision had its alternatives block. It had slipped into
present-tense "the stack runs with one command" before any code existed; I made it mark the docs
**design-phase / acceptance-criteria** so intent isn't read as shipped state.

## Task 4 — Adversarially review the ADR before I read it

**Prompt** `[critique-chain] [structure] [example]`:
> `<instruction>`Before I read the ADR, harden it. Spin up independent reviewers in parallel, each a
> different lens, and give the concurrency reviewer one job: **refute** the locking claims — treat them
> as wrong until proven otherwise.`</instruction>`
> `<output_shape>`One JSON object per finding so triage is mechanical:
> ```json
> {"severity":"major","file":"...","location":"...","suggested_fix":"...","confidence":"high"}
> ```
> `</output_shape>`
> I want the guarantees attacked, not admired.

**What came back:** five agents, **30 findings**. The concurrency skeptic **could not refute** the
four headline guarantees — it verified the `UPDATE … +1` lost-update safety via Postgres's
EvalPlanQual re-evaluation, the `FOR UPDATE` idempotency, the MVCC aggregate, and the
`ON CONFLICT … WHERE newer` guard. But it surfaced real gaps: the `FOR UPDATE` lock assumed a
pre-seeded row, `overspeed (3.0)` contradicted `position_jump (5.0)`, event anomalies risked unbounded
rows, and the ADR linked to a doc that didn't exist.

**Verification loop:** fixed every real finding, then re-checked mechanically —
`grep -rn "excluded.timestamp" docs/` → no matches; `ts`/`timestamp` reconciled; link-check clean.
The cosmetic nits I judged and waved through.

**My steering:** "couldn't refute" is the only acceptable result for a concurrency claim; a reviewer
that merely *agrees* hasn't done its job.

## Task 5 — Turn the ADR into TDD plans

**Prompt** `[goal+why] [example] [acceptance]`:
> Turn the ADR into two ordered, bite-sized TDD plans — backend and frontend. The concurrency tests
> are the plan's spine. `<acceptance>`**Zero placeholders.** Every load-bearing step ships runnable
> code — e.g. a step reads *"write `test_zone_counter_concurrency`: fire N concurrent `POST`s to one
> zone, then assert the count equals N"* **with the actual test body**, never "add a concurrency
> test."`</acceptance>`

**What came back:** two plans under `docs/superpowers/plans/` with exact paths, real code, and
commands. **Gate:** I spot-checked for the banned phrases ("add error handling", "etc.") — none.

**My decision:** execute inline with a **real browser-verify loop** (Task 8), not just unit tests.

## Task 6 — Build the backend

**Prompt** `[goal+why] [acceptance]`:
> `<goal>`Build the backend first, raw SQL so the locks are legible, organized as vertical slices.`</goal>`
> `<acceptance>`Two tests are the gate and must pass against a **real Postgres**: (1) 50 concurrent
> same-zone entries → count is exactly 50; (2) 20 racing fault events → exactly one maintenance record
> + one mission cancelled. Do not tell me it's done until `pytest` is green.`</acceptance>`
> `<constraints>`Minimal comments — only where intent isn't self-evident. Tests-first on the
> concurrency-critical paths.`</constraints>`

**Verification loop:** `pytest` → iterate → **17 passed**, including both proofs. The fault test is
the meaningful one: 20 concurrent `POST`s, assert *exactly one* open maintenance record — proving
`SELECT … FOR UPDATE` + idempotency + the partial-unique index actually serialize. Green against real
Postgres, not a mock (a mock would have defeated the point).

## Task 7 — Build the frontend

**Prompt** `[goal+why] [constraints]`:
> Build the dashboard in Feature-Sliced Design — `app → pages → widgets → entities → shared`,
> lower-only imports. shadcn-style primitives, **zod at the API boundary** (validate + infer types),
> TanStack Query for polling. The boundary is the only place untrusted data enters — validate there
> and nowhere else.

**Verification loop:** `npm run build` (`tsc -b && vite build`) → first run failed on a TS6 `baseUrl`
deprecation → removed `baseUrl`, kept `paths` → **clean build, 165 modules**. Type-checking the whole
graph was the gate, not "it looks right."

## Task 8 — Browser-verify loop (where the real bugs were)

**Prompt** `[verify-in-the-real-thing] [acceptance]`:
> `<goal>`Don't trust green unit tests. Drive the *running* dashboard with Playwright, screenshot it,
> read the screenshot back, and iterate until it genuinely works.`</goal>`
> `<assert>`The gate is four passing e2e: (1) 50 vehicle cards render; (2) a posted zone entry
> increments the live count; (3) a faulted vehicle shows "fault" on its card; (4) with the API
> aborted, the error state **and** the connection toast appear.`</assert>`
> `<rule>`Every failure is a real defect — root-cause it, fix it, re-run the whole suite,
> re-screenshot.`</rule>`

**Verification loop — three bugs that green unit tests and `curl` both missed:**
1. **CORS.** Playwright showed **zero vehicle cards**. `curl` had been perfectly happy because it
   isn't a browser and doesn't enforce CORS — the API had no CORS middleware, so the browser silently
   blocked every cross-origin fetch. *My insistence on a real browser is the only reason this was
   caught.* → added `CORSMiddleware`.
2. **Fault wasn't terminal.** With the simulator running, a faulted vehicle flipped back to `moving` —
   later telemetry overwrote the status, contradicting the ADR's own "fault is terminal" rule. The
   code didn't match its design doc. → `CASE` guard in the snapshot upsert.
3. **A 500 on the fault path.** A leftover open-maintenance row made the fault `INSERT` violate the
   partial-unique index. → `INSERT … ON CONFLICT … DO NOTHING` so the critical path can't crash.

After the fixes: **4 Playwright e2e + 17 backend tests green**, plus a screenshot of the live
dashboard. This task alone justified the "verify in the real thing" rule.

## Task 9 — Code-smell sweep + remediation

**Prompt** `[critique-chain] [structure] [example]`:
> Audit the whole codebase for smells across independent lenses — backend coupling, the SQL/data
> layer, backend quality, frontend/FSD, cross-cutting readability. **Respect the deliberate ADR
> choices** (raw SQL, vertical slices, polling) and hunt for smells *within* them. Findings as rows
> like `{severity: high, title: "status vocab duplicated across 4 sites", effort: M}`.

**What came back:** **41 findings** (7 high, 12 medium, 22 low), deduped into **8 themes**. The
dominant smell: the vehicle-status vocabulary hand-written in 4+ places.

**Verification loop:** fixed all 8 themes **behaviour-preservingly, one commit per theme, `pytest`
green after each** — the safety net caught any drift instantly. I deliberately **rejected two
findings** (the `post_status` 404 check is the contract; the read=pool/write=transaction split is
fine) and the sweep's flagged "circular dependency" was a **false positive** — no real cycle existed.

**My steering:** the bar was *fix the root cause, not the lint count*. Applying all 41 verbatim would
have been busywork plus one real mistake.

## Task 10 — Flatten the rule engine + frontend UX states

**Prompt** `[goal+why] [acceptance]`:
> The `anomaly_rules` logic is a nested if-chain — a smell. Flatten it; kill the cryptic variables and
> magic numbers. And the dashboard has no empty states, no loading skeletons, no robust error handler,
> and no success/error indicator — add them. Keep it behaviour-preserving on the backend; the tests
> prove it.

**What came back:** a flat **rule registry** (each rule a self-contained early-return function over a
`RuleContext`; `evaluate()` a one-line comprehension); descriptive names; named constants. On the
frontend: a reusable `QueryBoundary` (error / skeleton / empty / content), an app-level
`ErrorBoundary`, and `sonner` toasts wired to the query cache as a connection indicator.

**Verification loop:** **17 backend** (behaviour identical) + **4 e2e** — including a new test that
*aborts the API* and asserts both the error state and the connection toast appear.

**My steering:** I wanted the error handling **centralized**, not a per-widget `if (isError)` copy —
one `QueryBoundary` + one `ErrorBoundary` + one cache-level toast.

## Task 11 — Data-layer debate, slice queries, verified runbook

**Prompt** `[force-options]` — as an adversarial collaborator, told to argue both sides:
> I don't think skipping a dedicated data layer is right — should the SQL really sit with the business
> logic? I don't want too many layers, but this feels like too much. Lay out the 2–3 layering options
> (repository / Unit-of-Work / slice-local queries) with trade-offs, then **defend the one you'd
> actually choose. Stand your ground — don't just agree with me.**

**What came back:** it pushed back. The argument: here the SQL *is* the business logic — the
concurrency invariants live in the SQL *and the transaction boundary* — so a repository would hide the
isolation strategy, and because `ingest_event` runs five statements in **one** transaction holding a
row lock, a repository forces either broken atomicity or a leaky Unit-of-Work (*more* layers). It
recommended the middle: a slice-local `queries.py`, handler still owning the transaction.

**My decision:** agreed. SQL lifted into `queries.py` per slice — behaviour-preserving, 17 tests green.

**Verification loop (the doc, too):** I then asked for a precise local-run guide and made it **run
every command**. That immediately caught a real bug: the Dockerfile ran `pip install -e .` *before*
copying the source, so `docker compose up --build` failed (the host venv had masked it). → fixed the
build order + `[build-system]` + `.dockerignore`, re-verified: `docker compose up` healthy,
`docker compose exec api pytest` → 17 passed, `npx playwright test` → 4 passed.

---

## Task 12 — Make the simulator behave like a real fleet

**Prompt** `[goal+why]`:
> The dashboard's statuses look like they're looping with no logic and cycling all together. The
> simulator (the edge-client stand-in — *not* the service, which only records what's reported) is
> picking status/speed/battery at random every tick. Replace it with a coherent per-vehicle lifecycle
> so the fleet tells a believable story. Faults stay operational (raised via the status endpoint), not
> random.

**What came back:** a sticky per-vehicle state machine — `idle → moving (mission) → battery drains →
charging (recharges) → idle` — with speed and battery tracking the *final* status each tick, position
drift bounded to how far the vehicle could actually travel, and `zone_entered` firing only on a real
crossing.

**Verification loop — and it caught three bugs in my *own* new code.** I treated the **anomaly mix**
as the gate, and the first run produced `position_jump:281` (my wander step was ~11 m/tick ⇒ implied
~11 m/s, over the 8 m/s teleport bound), `state_inconsistent:22` (a vehicle ending its mission kept
the moving speed on the idle tick), and `charging_no_gain` (the moving→charging tick still drained,
plus a startup artifact from vehicles that *began* charging vs the seeded 100%). Fixes: decide the
transition first then apply effects to the final status; bound the wander to the vehicle's real speed;
start the fleet idle/moving. Re-verified against the live API — speed matches status, the full
idle/moving/charging lifecycle plays out, and the only anomalies are meaningful `low_battery`.

**My steering:** a coherent state machine over random data, and the simulator isn't "done" until it
stops emitting spurious anomalies — the same "verify in the real thing, root-cause every failure" bar
I held the service to, applied even to a throwaway tool.

## Reflection

- **Strongest at breadth and structure.** Synthesizing MADR / VSA / FSD, drafting a complete ADR with
  genuine alternatives-and-rejections, scaffolding two subsystems fast. The **parallel adversarial
  review** was the single highest-leverage move — independent skeptics caught precision gaps a single
  pass ships.
- **Weakest at judgment and "does it actually run."** Left to its defaults it reached for the *easy*
  option (SQLite) over the *instructive* one, **forgot CORS**, and shipped a **broken Dockerfile** —
  the integration/run-reality failures unit tests and `curl` never expose. The browser loop and the
  act of *running the runbook*, not the model's confidence, found the real bugs.
- **A useful pair pushes back.** Asked to add a data layer, the right move was to argue *against* it
  with reasons and offer the proportionate alternative — not comply. A model that just obeys would
  have added the wrong abstraction.
- **Review fan-out is high-recall, not high-precision.** 41 smells surfaced fast, but several were
  facets of one problem and one was simply wrong. Triage — dedup, reject false positives — stays a
  human call.
- **Refactors are only safe because the tests gate them.** Flattening the rule engine and renaming
  across the data path look safe and aren't; "behaviour-preserving, green after each step" is what
  made the AI's large mechanical edits trustworthy.
- **The pattern that worked:** AI for breadth (research, drafting, fan-out review, scaffolding) + me
  for direction and the gate (forcing alternatives, demanding a real browser, treating every failure
  as a root-cause fix, deciding which findings are real, and never accepting "done" without running
  it). The leverage was large — but it came from *driving and verifying* the AI, never from trusting
  the first green check or the first finding list.
