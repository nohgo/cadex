---
name: cadence-layout
description: Plan, implement or review analog IC layout and physical verification using an established project technology, device setup and DRC/LVS/extraction flow.
---

The UF gpdk180 native Assura DRC/LVS and Quantus extraction route is now
verified on a scratch design. Use [tool recipes](../cadence-virtuoso/references/tool-recipes.md)
and cadex drc/lvs/pex for that bounded profile, rather than rediscovering retired
Diva/RCX paths. Other technologies still require their actual project runsets.

Establish the authorized schematic/layout targets, schematic/netlist revision,
PDK/technology, device variants, units/grid, layer and via rules, and the actual
project verification tools/runsets. Reuse existing project procedures. Do not
invent technology values, executable flags, verification decks or API signatures.
Missing project tooling is a concrete readiness gap; report it and continue
independent planning without claiming a verified implementation.

Preserve device parameters, multiplicity/fingers, body/well connectivity and
interface intent. Plan current/signal paths, matching and symmetry where relevant,
orientation, common environment, sensitive-node parasitics, routing accessibility,
contacts/taps and supply returns. Base physical constraints on the technology and
design requirements. Review spacing, routing clarity, label/pin placement and
readability alongside electrical constraints; geometric plausibility is not DRC.

Use [cadence-virtuoso](../cadence-virtuoso/SKILL.md) for exact existing-view
routing, verified editing APIs, write-lock handling and live session boundaries.
The current managed live helper can inspect/edit layout but its automatic
`--save` checker gate supports schematics only. Establish a verified,
layout-specific check/save path before a saved layout task; do not bypass this
limitation with raw JSON saving or an unreviewed API sequence. Do not create a
missing layout through a misspelled live target; intentional new-view creation
requires the user's task scope and a verified creation flow.

Run the requested physical checks on the actual saved layout with its matching
schematic/netlist and correct runsets. Inspect DRC diagnostics and LVS devices,
ports, parameters and connectivity; a tool exit or report file alone is not a
pass. Record versions/input identity and unresolved violations. Extraction and
[post-layout simulation](../cadence-simulation/SKILL.md) must identify the
extracted view/netlist and compare the relevant metrics with pre-layout evidence.
Mark affected checks stale after edits. Distinguish layout saved, DRC clean,
LVS matched, extracted performance and visual review. The verified site profile
does not establish another PDK's runsets or certify a new design.
