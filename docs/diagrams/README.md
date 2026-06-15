# Diagrams

Rendered with Mermaid (GitHub renders these natively; VS Code with the Mermaid extension also
works). They illustrate the decisions in [`../adr/0001-fleet-telemetry-architecture.md`](../adr/0001-fleet-telemetry-architecture.md).

| # | Diagram | What it shows |
| - | ------- | ------------- |
| 01 | [System context](01-system-context.md) | Containers: vehicles, API, dashboard, Postgres |
| 02 | [Data model (ER)](02-data-model-er.md) | The six tables and their relationships |
| 03 | [Telemetry ingest flow](03-flow-telemetry-ingest.md) | Insert + snapshot upsert + zone counter + anomaly detection, in one transaction |
| 04 | [Fault transition flow](04-flow-fault-transition.md) | Atomic, idempotent mission-cancel + maintenance under a row lock |
| 05 | [Zone counter flow](05-flow-zone-counter.md) | Two vehicles entering the same zone concurrently; no lost update |
