# AI-Driven SDLC — How This Build Is Run

This project is as much a demonstration of *how to build with AI* as it is a telemetry service. This
document describes the **process**; the turn-by-turn prompt record lives in
[`../AI_INTERACTION_LOG.md`](../AI_INTERACTION_LOG.md).

The governing idea: **the human sets direction and holds the quality bar; the AI does the
breadth-first labor** — research, drafting, decomposition, parallel review — under explicit approval
gates. AI is treated as a fast, literal, tireless pair, not an oracle. Every load-bearing claim is
verified (by a test, an independent agent, or a doc) before it is trusted.

## The phases

| Phase | What the AI does | What the human (Marcelo) owns | Guardrail |
| ----- | ---------------- | ----------------------------- | --------- |
| **0 · Frame** | Restate the brief, surface ambiguities and open decisions | Goals, scope, the "showcase AI productivity" intent | The brief itself; explicit assumptions list |
| **1 · Design** | Research patterns (MADR, vertical slice, FSD), propose 2–3 options per fork with trade-offs | **Decides every fork** (Postgres, hybrid anomaly, polling, vertical slice, FSD…) | Structured choice prompts; nothing built before sign-off |
| **2 · ADR** | Author the consolidated ADR + design docs + diagrams | Direction, conventions, the "alternatives + why rejected" requirement | MADR structure; design-before-code gate |
| **3 · Adversarial review** | Run 5 independent review lenses (concurrency skeptic, MADR completeness, spec coverage, consistency, render checks) in parallel | The bar: "harden the claims before I read it" | Findings must be triaged and fixed; a skeptic *tries to refute* |
| **4 · Plan** | Turn the ADR into an ordered implementation plan with checkpoints | Approve / reslice | Plan reviewed before code |
| **5 · Implement** | Write code slice by slice, tests first for the concurrency-critical paths | Review diffs, correct course | **Tests as executable spec** — the concurrency tests are the proof of the ADR |
| **6 · Verify** | Drive the running app with Playwright, capture screenshots, iterate | Confirm it actually works | Real browser + real Postgres, not assertions of success |
| **7 · Review** | Self-review the diff for bugs and simplifications | Final acceptance | Independent review pass before merge |

The phases are not strictly linear — phase 3 feeds back into phase 2, and phase 6 feeds back into
phase 5 — but each has an explicit gate the human controls.

## Why an adversarial review phase

The most important AI-specific practice here is **not trusting the first draft**. After the ADR was
written, five independent agents reviewed it in parallel, each with a different lens, and the
concurrency lens was instructed to *refute* the locking claims rather than confirm them. It could
not refute the four headline guarantees (that is the signal we wanted), but it surfaced real
precision gaps — a `FOR UPDATE` precondition, a threshold contradiction, an unbounded-anomaly-rows
risk, a dangling deliverable — that a single pass would have shipped. Independent verification is
cheap with agents and disproportionately valuable: it is the antidote to confident-but-wrong AI
output.

## Tools in the loop

- **Claude Code** as the agent harness (this build).
- **Context7** for current library docs (MADR primer, FSD, Scalar/FastAPI, Mermaid) instead of
  relying on training-cutoff memory.
- **Workflow orchestration** — parallel subagents for the multi-lens review (and, later, for
  parallel implementation/verification where work is independent).
- **Playwright** for the browser-verification loop in phase 6 — the AI sees what the user sees.
- **Tests + git** as durable state across context windows.

## Principles applied (from prompt-engineering best practice)

- **Clear and direct, with motivation.** Prompts state *why* (e.g. "so the grader can *see* the
  isolation mechanism"), which steers better than terse commands.
- **Examples over description.** Where output shape matters (schemas, the findings format), give an
  example, not an adjective.
- **Structure with tags / schemas.** Review agents return a validated JSON schema, not prose, so
  findings are machine-triagED.
- **Let it think, then verify.** Adaptive reasoning for design; explicit self-check ("try to
  refute") for correctness.
- **Parallelize independent work.** Research fetches and review lenses run concurrently.
- **Human approval gates.** No code before an approved design; no merge before review.

See [`../AI_INTERACTION_LOG.md`](../AI_INTERACTION_LOG.md) for the actual prompts, the AI's output,
and the corrections made at each step.
