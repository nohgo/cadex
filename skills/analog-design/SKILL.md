---
name: analog-design
description: Design or revise analog transistor circuits, including topology, sizing, bias, loads, interfaces, and operating conditions. Use for circuit engineering beyond an isolated geometry edit.
---

Establish the intended function and required fidelity: topology demonstration,
biased operating circuit, or performance target. Inspect the existing circuit,
PDK/device family and project context before choosing supplies or device values.
Separate user requirements, inherited project choices and provisional assumptions.
Resolve a missing choice when it materially changes architecture or validity;
use supported context for routine choices and report consequential assumptions.

For an operating circuit, account for the full DC current path, supplies/returns,
bulk ties, input/output interfaces, bias generation or external bias ports, and
the output load/termination. Trace where current enters and leaves each branch.
An exposed DUT output may be intentional when a bench provides its load. An
unexplained floating terminal or a topology alone is not a working amplifier.
For a topology-only change, identify what remains to make it operate without
silently extending the requested scope.

Choose initial sizing/bias from the requested operating range, PDK constraints
and first-order estimates. Consider device stress, current, headroom, gain,
swing, loading and relevant speed/noise tradeoffs. Keep equations and estimates
distinct from model-based measurements; device-region labels alone do not prove
adequate margin. Preserve parameter expressions and CDF callbacks unless the
design change requires otherwise. Do not invent missing specifications or
declare optimization complete without an objective.

For schematic implementation, use [cadence-virtuoso](../cadence-virtuoso/SKILL.md)
and its circuit-aware editing reference for complete local geometry, readable
placement, connectivity assertions and intentional check/save. Verify the named
objects and read back actual device parameters, interfaces and connections.

Hand simulation a clear contract: DUT/port order, supply and bias conditions,
source/load impedance, operating range, required analyses and observables with
units and acceptance limits. The [simulation skill](../cadence-simulation/SKILL.md)
owns constructing and validating that bench. For a working-circuit claim,
establish a valid operating point before interpreting small-signal or dynamic
performance. Choose further checks proportional to the requested function.
Report what operates, what was measured and what remains an assumption.

Use [analog-design-flow](../analog-design-flow/SKILL.md) when coordination or a
continuing design record is useful; a single design edit need not create one.
