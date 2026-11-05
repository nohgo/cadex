# Managed live jobs

Use this for a named schematic/layout change in an explicitly opted-in GUI.
Use `~/.codex/scripts/virtuoso-live` (abbreviated below as `$LIVE`), with the
tool's workdir set to the project containing `cds.lib`. Request reviewed
execution on the first invocation as specified in the skill. Do not write
Python transport scripts, invoke a bare interpreter, or reload the bootstrap.

## Inspect, implement, check

```bash
LIVE=~/.codex/scripts/virtuoso-live
"$LIVE" status
"$LIVE" inspect --library LIB --cell CELL --view schematic
"$LIVE" new-job --name descriptive-change
# Write SKILL to the returned absolute job path, then:
"$LIVE" skill /absolute/returned/job.il --library LIB --cell CELL --view schematic --save
```

Add `--session ID_FROM_STATUS` when explicit session selection is necessary.
Do not select a session merely because it is a running process. Inspection
uses the exact existing view and reuses its editor; if closed, it opens an
editable editor honoring locks. It does not save or change circuit data.
It returns instance masters/origins/orientations/bounding boxes, transformed
pin boxes, terminal-net maps, CDF parameters, wires and labels. CDF/property
values are printed SKILL representations, preserving types and expressions.
The `modified` field uses `dbIsCellViewModified`, not `cv~>modified`.

Jobs contain only the requested circuit operation. The managed context supplies
`cadexCV`, `cadexWindow`, and `cadexRunDir`. Inspect actual names, coordinates,
masters and parameters first; assert assumptions before mutation. Return
JSON-compatible scalars/lists with `cadexReport(...)`, never database handles.

Verified recipes loaded for every managed job:

| Recipe | Purpose |
| --- | --- |
| `cadexInst("I3")` | Exact, unique named instance in the target. |
| `cadexInstTerm("I3" "G")` | Exact terminal association. |
| `cadexPin("I3" "G")` | Transformed pin center; rejects ambiguous multi-shape pins. |
| `cadexCreate("LIB" "MASTER" "NEW_NAME" x:y "R0")` | Create from an existing symbol master; refuse name collisions. |
| `cadexParam("I3" "w" "2u")` | Apply an actual CDF parameter and read it back; preserve PDK callbacks. |
| `cadexPinEscape("I3" "D" 0.5)` | Inspect opposing pins to obtain an outward schematic segment; supports rotations/mirrors. |
| `cadexStub("I3" "D" "out" 0.5)` | Create a checked wire and named label, with a net assertion in managed live jobs. |
| `cadexWire(list(x1:y1 x2:y2 ...))` | Create a schematic wire with the tested UF IC618 signature. |
| `cadexMoveFigures(list(figures...) dx:dy)` | Move an explicitly inspected local group; deduplicate parents/children so attached labels move once. |
| `cadexStretchWire(oldPoints newPoints)` | Change one straight axis-aligned wire in place; retain attached labels and their fractional anchors. Reject unsupported routing before changing it. |
| `cadexDeleteWire(list(...))` | Delete exactly one inspected wire; refuse attached figures rather than silently deleting labels. |
| `cadexRequire(condition "message")` | Fail a precondition explicitly. |
| `cadexExpectConnection("I3" "G" "V0" "PLUS")` | Declare an intended connection, checked after extraction and before saving. |
| `cadexExpectNet("V0" "MINUS" "gnd!")` | Declare an intended net identity. |
| `cadexDescribe()` | Fresh complete target snapshot. |

For `analogLib/vdc`, the actual voltage CDF parameter is **`vdc`**.
`cadexParam("V0" "vdc" "0.7")` uses its callback-free native string parameter;
`"dc"` is accepted as an explicit alias only for that master. Other parameters
still require their real CDF names and callback path. An arbitrary stored property
can exist yet be ignored by the netlister: confirm effective values in the native
simulation deck when testing a parameter path, including expressions/units.

For a coherent operation, group creation, parameter changes, local wire/ground
adjustments, assertions and task output in one job. These are primitives; the
agent still decides circuit topology and readable placement. Moving an origin
alone does not stretch wires. Select local wires/grounds explicitly, preserving
shared routing; the helpers do not infer the circuit neighborhood. Include attached
labels freely in a move group; ownership is deduplicated. Stretch retains text,
orientation and ownership, but label readability and circuit connectivity still
need review. See [circuit editing](circuit-editing.md).

For unfamiliar calls, run `"$LIVE" api FUNCTION`. This consults the small
verified index and installed release documentation without contacting a GUI.
If absent, search the installed Cadence manuals under `/apps/cds/IC618/doc`;
do not invent names or signatures. `dbFindOpenCellViewByName` takes three
strings; `dbFindOpenCellView` takes a library ID. Neither is a hypothetical
`dbFindOpenCellViewByType`. Use `drain(port)` for stream flushing.

## Save and failure behavior

For a finished schematic edit use `--save`. Before mutation it refuses existing
unsaved work, runs baseline `schCheck`, and refuses baseline errors. After the
job it reruns checking, requires zero errors and no warning-count regression,
checks declared connections, and calls `dbSave`. Connectivity extraction and
schematic rules must be enabled; report the cross-view rule flag too. Inspect
diagnostics and geometry: equal warning counts do not prove unchanged warnings,
and checking does not prove intended topology or readability.

Saving includes the entire view. Use `--allow-existing-edits` only with explicit
authorization to include the existing pending work. Otherwise report that
boundary before proceeding. Omit `--save` for an explicitly requested preview.
Managed layout saving is currently unsupported; use the appropriate verified
layout check/save flow rather than bypassing the schematic gate silently.

Completion requests redraw for every target, including inspection, and fits the
cell bounding box only when it opens a new editor. Reused editors retain their
viewport; focus is not raised or changed. This is a paint request, not proof of
what TigerVNC displays. Database verification and visual verification stay separate.

The result contains `baseline_check`, `final_check`, `saved`, task `result`,
and a fresh `readback` after checking/saving. Verify those values and the
task's terminal/parameter/geometry invariants. Each run writes a copied `job.il`,
`request.json` (source hash, target/session; no nonce), `result.json` or
`failure.json`, and `status`. Successful completion requires status 0, completion.ok and
result.json, plus actual task evidence. No automatic replay occurs. A failed
job/check/timeout may leave partial edits; inspect the named view before a
repair. Never close/discard the editor to recover.

Jobs and audit runs live under `~/.local/state/cadex/live/{jobs,runs}`, outside
the working project. Keep helper source and recipes in Cadex Git, deployed by
the installer into `~/.codex/share/cadex-live`. Do not edit installed copies or
commit generated jobs, session registrations, design databases, PDK code or
tokens. Managed SKILL is trusted reviewed code, not an in-process security
sandbox; lifecycle guards reject accidental exit/save/close/load glue.
