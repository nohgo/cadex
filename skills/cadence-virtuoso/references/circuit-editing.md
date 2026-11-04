# Circuit-aware edits and review

Apply these semantics to live and saved schematic/layout edits. A named object
anchors the requested design change; it does not necessarily bound the affected
geometry. Routine consequences of the request are the agent's responsibility.

## Plan the smallest complete change

Inspect the authorized target's instance inventory and local neighborhood:
master, transformed terminals, nets, wires, branches, local ground/supply
symbols, labels, annotations, orientation, grid and spacing. Resolve an exact
name first; a unique case-insensitive match may resolve capitalization without
another user turn. Report the actual name used. Ask when several candidates or
several materially different circuit interpretations remain.

For “move this source,” preserve the intended circuit. Move attached local
geometry together or stretch connections to fixed external anchors. Include a
local ground branch and owned labels when appropriate. Do not drag a shared bus,
an entire connected circuit, or another functional block. Do not leave wires at
old pin locations. A raw instance-origin assignment is appropriate only when
inspection establishes that no dependent geometry needs adjustment, or when the
user explicitly requests an isolated geometry experiment.

Keep preconditions specific to each requested operation. A parameterized V0
voltage must stay unchanged during a V0 placement edit; it is not a reason to
block a separate numeric V1 voltage change. Distinguish instance identity,
electrical parameter values, display annotations and geometry. Preserve units,
CDF callbacks and expressions unless changing them is part of the request.
Group related operations for one design change into one coherent job.

## Preserve electrical and geometric invariants

Record the original terminal-to-net map, local connection geometry, intended
fixed anchors and affected objects. Verify both database associations and actual
wire endpoints at transformed pins. Existing net objects can conceal an
unconnected drawing until schematic checking extracts connectivity again.
Detect new open ends, unintended shorts/junctions, net merges/splits, detached
labels and changes outside the planned region. Preserve intentional existing
opens and distinguish old diagnostics from newly introduced ones.

## Review readability

Check symbol/text overlap, labels covering pins or wires, crowded objects,
near-touching conductors, confusing crossings, unnecessary bends, long wire
runs and a tangled-looking neighborhood. Keep consistent grid alignment,
reasonable spacing, clear signal flow and recognizable local ground/supply
placement. Use bounding boxes, pin/wire geometry and spacing checks where
available; disclose when the visual result still needs TigerVNC observation.
Connectivity or a clean checker result alone does not establish readability.

Prefer meaningful named nets when they make long or crossing connections
clearer. Keep short, obvious local wires when they communicate the circuit
better. Place labels unambiguously on the intended nets. Avoid clutter from
unnecessary labels. Do not silently rename existing nets, change global/local
scope or hierarchy semantics, or merge nets through duplicate names.

## Finish with checks and an intentional save

For a completed, authorized edit, the normal finish is review, check, verify,
and save. An explicit user request for an unsaved preview overrides that finish.
Inspect-only jobs must not save. In a live GUI, saving commits the whole view,
including pre-existing unsaved work: establish that baseline first. If unrelated
pending work would also be committed, get a decision for that whole-view save
or use an authorized scratch copy. Do not silently include it.

For a schematic, use the installed release's programmatic `schCheck(cv)` and
inspect **both returned counts**: `car(result)` is errors and `cadr(result)` is
warnings. The returned list being non-nil is not evidence of success. Verify
whether connectivity extraction and relevant schematic/cross-view rules were
enabled (`updateConn`, `runSRC`, `runVIC`); report skipped checks. Do not weaken
checks or change saved settings to obtain a pass.

`schCheck` can update connectivity. Recheck the intended terminal/net and
geometric invariants after it runs. Fix errors introduced by the edit before
saving. Review and report warnings, including their baseline/delta; do not
silently accept a new warning that contradicts intent. Then call `dbSave(cv)`,
check its result, and read back the saved task-specific data. Do not discard or
close the live editor. Never save a known failed or partial edit merely to
complete the workflow; retain it visibly and report its state when a safe repair
is unavailable. A failed save/check is not task completion.

These APIs do not require mouse/CIW automation: they can run in the connected
process or a separate authorized batch process. Do not open a second writer
against a live GUI's lock. For layout, use the project's appropriate checks;
saving is not evidence of DRC/LVS or post-layout performance. Match verification
to the change and report precisely what was exercised.

## Helper capability boundary

The managed `inspect` command provides the named view's neighborhood. Managed
SKILL jobs provide reusable creation, parameter, pin, wire and verification
recipes with one target/session context, an explicit checker/save gate and an
audit record. See [Managed live jobs](live-jobs.md). The agent must plan the
smallest complete circuit change using these tools; a raw JSON move still only
changes an origin and does not stretch wires. Do not present that primitive as
a complete connected-component move. Group or stretch local geometry according
to the inspected circuit, using verified Cadence APIs when a recipe is absent.

Managed SKILL is trusted, reviewed code, not a security sandbox inside Virtuoso.
Respect target scope and do not hide additional operations in another load or
evaluation layer. Lifecycle/save guardrails catch accidental batch glue. On
failure, inspect before retrying; preserve pre-existing work and the GUI.

## Acceptance cases for the helper extension

Test scratch views with a voltage source and local ground/wire branch; components
connected at both ends; shared buses and junctions; rotated/mirrored symbols;
parameter and net labels; nearby obstacles and off-grid requests; intentional
opens; similar instance names; numeric and parameterized voltages; pre-existing
unsaved edits; checker errors/warnings; and failed saves. Include already-open
and closed-view routing, fresh-client reverse edits and preserved GUI lifetime.
Require correct connectivity, reasonable readability, and the requested save
state. A helper exit code or moved origin alone is insufficient.
