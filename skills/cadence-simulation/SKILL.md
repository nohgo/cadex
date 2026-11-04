---
name: cadence-simulation
description: Design analog testbenches, run Spectre/ADE/OCEAN or existing Xcelium/AMS flows, and verify measurements and waveforms against circuit requirements.
---

For UF native execution use the [verified tool recipes](../cadence-virtuoso/references/tool-recipes.md)
and installed cadex netlist/spectre/psf commands. They contain site setup,
netlisting output and release-specific mechanics; retain per-command review on
the first licensed invocation. Inspect native evidence and task metrics, not just
a manifest's completed state.

Start from the question the test must answer, the exact DUT and its source
identity. Read [testbench design](references/testbench-design.md) when creating
or changing a bench. Read [execution and results](references/execution.md) for
tool setup, netlisting, run commands, diagnostics and waveform delivery.

Analog design supplies the intended function, operating conditions and success
criteria; this skill owns bench implementation, bench validation, analyses and
measurements. If those conditions are missing, inspect the project context or
use [analog-design](../analog-design/SKILL.md) to resolve the material decisions.
Bench-only requests are valid; do not redesign the DUT merely to make a test pass.

Reuse a working bench/config and its PDK/model bindings. Regenerate the netlist
after design/view-binding changes and verify its interfaces against the actual
saved DUT. A hand-written approximation or old deck cannot verify a new
schematic; label such results by their actual provenance. Live netlisting and
saving must account for pending GUI edits and write locks via
[cadence-virtuoso](../cadence-virtuoso/SKILL.md).

For a new biased analog circuit, validate the DC solution and meaningful device
headroom before interpreting AC/transient results. Select analyses and sweeps
that can falsify the requested behavior; avoid automatic exhaustive runs. Match
thresholds, tolerances, units and operating conditions to the design contract.
Check native status, causal diagnostics, completed analyses, finite data and
task-specific measurements. A clean schematic checker or simulator exit alone
does not establish electrical success.

Record source/netlist/bench identity, models/corner, variables, analysis options,
exact command, run directory and measured results. Invalidate affected results
when inputs change. Keep the project's supported run layout and relative include
resolution; otherwise use the configured results area and its labeled run manifests. Tool probes and live transport artifacts belong in Cadex state, not among
schematic files. Report pass/fail/inconclusive per requested metric; separate
electrical results from database checks and visual readability.
