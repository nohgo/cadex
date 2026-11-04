# Analog skill split — November 4, 2026

The maintained source is in Cadex Git. Seven skills install together: the five
analog/workflow/tool skills plus the existing, unchanged SV and VAMS skills.
Each entrypoint is short and routes detailed material to relevant references.
Testbench design is a distinct stage owned by simulation; analog design supplies
the operating conditions and acceptance criteria. Delegation is optional and
conditional on available tools/authorization, with one owner integrating work
and serialized design mutations. No subagent framework or settings were added.

## Independent installation and helper verification

- **29 tests passed** on `ece-lnx-08`, using Python 3.11 and SkillBridge 1.8.0.
- The five new packaging tests cover all seven skills/resources, idempotent
  reinstall with an existing consent fixture preserved, known global-instruction
  upgrades preserving surrounding user text and backups, refusal of unrecognized
  global edits/incomplete bundles before deployment, and valid resource links.
- All seven skills passed the skill-creator frontmatter/completeness validator.
- Deployed skill resources match source byte for byte. The global ECE routing
  section migrated from its known prior version through the existing installer.
- Live runtime code, batch launcher, bootstrap, shell startup and saved Codex
  configuration were unchanged. Existing digital/modeling skills were unchanged.
- Tests used temporary homes and their own socket fixtures. No GUI was contacted
  and no Cadence license was acquired by this work.

Test log: `/tmp/cadex-design-flow-tests.log` on ECE. Source tests:
`tests/test_install_flow.py`, the existing helper/installer suite, and the
synthetic cases under `tests/evals/analog-flow/`.

## Fresh VM Codex behavioral checks

Three independent native VM Codex sessions received only the task from each
case plus `design.json` in a private scratch project. Tasks did not name a skill
or disclose the review rubric. Each explicitly requested documentation-only work
and prohibited real design edits, GUI contact and EDA execution. All sessions
used the existing per-command review mechanism; no follow-up steering was sent.

| Case | Observed result |
| --- | --- |
| Working circuit | Discovered flow/design/simulation skills and the bench reference; identified the missing DC output load/current path, proposed a resistive-load candidate, kept biases provisional, and defined operating-point/gain handoffs without claiming measured success or starting unsolicited layout. |
| Bench only | Discovered simulation and bench guidance, consulted analog design for the missing load, retained DUT connectivity/sizing, identified missing models/port-order evidence, and distinguished proposed characterization conventions from actual gain requirements. No DUT edits or measurements were claimed. |
| Layout readiness | Discovered layout/flow guidance, identified missing load/model/technology/runset inputs, avoided assuming equal geometries imply a matched pair, and separated planning from DRC/LVS/extracted-performance evidence. |

All three CLI exits were 0. Command audits showed only fixture/document reads,
hashing and documentation work; every source fixture hash remained unchanged.
Engineering/layout records stayed in the scratch project's
`.cadex/designs/eval_lib__cascode/`, as intended. No tooling files were written
in the user's working Cadence project.

These checks verify instruction discovery and planning behavior, not electrical
performance, licensed simulation, GUI behavior or a working UF physical flow.
The current managed helper's automatic check/save gate remains schematic-only;
the layout skill requires an established layout-specific path before saved work.

Private VM-local prompts/events/final responses and scratch records:
`~/.local/state/cadex/skill-evals/analog-flow_20261104T060024Z_eqqukjbo/`.

Session IDs:

- Working circuit: `01a1a524-f9d3-7451-990d-2a6768dcd0a4`
- Bench only: `01a1a526-4d5c-77f3-a3e1-e7fa60bfde2d`
- Layout readiness: `01a1a527-25d4-7f93-aa72-533b5a68f65e`

For repeat evaluations, copy only `design.json` into a new temporary project and
give a fresh VM Codex session the selected case's `task`. Keep `review` criteria
outside its prompt/workspace, inspect its actual skill reads and outputs, and
retain the documentation-only restrictions. Do not use a working GUI/design as
the evaluation fixture.
