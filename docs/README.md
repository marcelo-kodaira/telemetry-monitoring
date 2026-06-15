# Documentation

Design-phase documentation for the fleet telemetry monitoring service. Start with the ADR.

| Document | What it is |
| -------- | ---------- |
| [`running-locally.md`](running-locally.md) | **Precise, verified run guide** — prerequisites, one-command stack, tests, simulator, troubleshooting |
| [`adr/0001-fleet-telemetry-architecture.md`](adr/0001-fleet-telemetry-architecture.md) | **The ADR** — every key decision with alternatives considered + why rejected, the four required questions, and consequences (MADR-influenced) |
| [`architecture.md`](architecture.md) | Vertical-slice (backend) + Feature-Sliced + atomic design (frontend), repo map, coding standards, test strategy |
| [`concurrency-and-isolation.md`](concurrency-and-isolation.md) | Per-operation isolation reasoning — the naive-wrong vs our-approach, with SQL, isolation level, and the test that proves each claim |
| [`api-contract.md`](api-contract.md) | Endpoint request/response/error contracts, query-param semantics, batch behavior, Scalar curation plan |
| [`diagrams/`](diagrams/) | Mermaid: system context, ER model, and the ingest / fault / zone-counter flows |
| [`ai-driven-sdlc.md`](ai-driven-sdlc.md) | How AI drives each phase of this build (process) |
| [`../AI_INTERACTION_LOG.md`](../AI_INTERACTION_LOG.md) | The turn-by-turn prompt record + corrections + reflection (living) |

**Reading path:** ADR → concurrency-and-isolation → diagrams → architecture → api-contract.
