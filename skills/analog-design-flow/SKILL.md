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

Read the relevant skill when entering its stage. A single agent can perform the
whole flow. Skills are instructions, not separate workers. If delegation tools
are available and permitted, independent analysis, bench planning or result
review may be delegated with the target, requirements and artifact paths. One
owner integrates results; serialize design mutations and GUI requests. Do not
require delegation, create one worker per skill, or change agent settings.

Read [project format](references/project-format.md) when establishing project
paths, creating a new workspace or organizing evidence. Use
`~/.codex/scripts/cadex project show` to resolve the actual launch, results and
agent directories. Preserve existing projects; full scaffolding is optional for
small experiments. For substantial work use [the record template](assets/design-record.md)
in the configured agent/designs/<design>/ area. Record requirements, assumptions,
input identities, conditions, measurements, evidence paths and the next step.
Reusable tooling belongs in Cadex Git; private designs/vendor data do not.

Treat testbench planning as a distinct stage: analog design defines what must be
demonstrated and under which conditions; simulation implements and validates the
bench and measurements. Resolve missing inputs at that boundary. Reuse existing
project decisions; ask only when a missing choice materially changes the result.

Before reporting completion, compare the evidence with the requested outcome.
After a schematic, model, bench, corner or variable change, mark affected prior
results stale until rerun on matching inputs. Separate topology/connectivity,
operating-point validity, measured performance, physical verification and visual
readability. If a stage is blocked, retain verified progress and name the missing
input/tool rather than silently lowering the goal or claiming the whole flow passed.
