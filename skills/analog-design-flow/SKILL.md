---
name: analog-design-flow
description: Carry an analog circuit or IC block through requested design and verification stages, preserving requirements and evidence across schematic, simulation, and layout work.
---

Translate the request into an engineering outcome and a stopping point: topology
edit, operating circuit, measured performance, layout, or extracted verification.
Use the stages necessary for that outcome. A local object edit does not imply a
new testbench or a complete IC implementation. Explicit user constraints govern
the flow; an existing GUI connection does not authorize unrelated design work.

## Route by the work needed

- Circuit architecture, sizing, bias, loads and interfaces: [analog-design](../analog-design/SKILL.md).
- Testbench design, analyses, execution and measured results: [cadence-simulation](../cadence-simulation/SKILL.md).
- Placement/routing, matching, DRC/LVS and extraction: [cadence-layout](../cadence-layout/SKILL.md).
- Named-view inspection/editing, live/batch execution and checked saves: [cadence-virtuoso](../cadence-virtuoso/SKILL.md).

Use the relevant skills as the work calls for them, whether collaborating on a
design or carrying a delegated block through the flow. Skills are instructions,
not separate workers. If delegation is available and permitted, analysis, bench
planning or review can be shared with the target, requirements and artifact
paths. Integrate the results and serialize design mutations and GUI requests.

Navigate the existing project's layout, instructions and design records. Use
`~/.codex/scripts/cadex project show` to resolve configured launch, results and
agent directories. Read [project layout guidance](references/project-format.md)
when paths or evidence organization need clarification; its scaffold is an
optional starting point for new workspaces. [The record template](assets/design-record.md)
can help when a new design record is useful. Retain requirements, assumptions,
input identities, conditions, measurements, evidence paths and the next step in
the project's records. Reusable tooling belongs in Cadex Git; private
designs/vendor data do not.

Treat testbench planning as a distinct stage: analog design defines what must be
demonstrated and under which conditions; simulation implements and validates the
bench and measurements. Resolve missing inputs at that boundary. Reuse existing
project decisions and discuss unresolved choices when collaboration would help.

Before reporting completion, compare the evidence with the requested outcome.
After a schematic, model, bench, corner or variable change, mark affected prior
results stale until rerun on matching inputs. Separate topology/connectivity,
operating-point validity, measured performance, physical verification and visual
readability. If a stage is blocked, retain verified progress and name the missing
input/tool rather than silently lowering the goal or claiming the whole flow passed.
