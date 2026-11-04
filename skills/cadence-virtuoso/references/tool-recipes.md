# Verified UF native-tool recipes

Use `~/.codex/scripts/cadex --help` for typed commands. Run from the configured
Cadence launch directory (or give global `--project DIR`). For every **licensed**
`skill`, `netlist`, `spectre`, `drc`, `lvs`, or `pex` invocation, request
`sandbox_permissions="require_escalated"` on the first attempt, with the tool
workdir set to that launch directory and justification naming the project and
operation. Keep review per command. Pure project discovery, scaffolding, status,
preflight, PSF inspection and file work do not inherit blanket escalation.

This is the successful UF gpdk180 route from the FVF test: Virtuoso/OCEAN →
Spectre 25.1; Assura 4.1 for DRC/LVS; Quantus 22.1 for extraction. It is a site
profile to validate against actual execution, not a promise of future licenses
or arbitrary PDK support. Reuse established project runsets for other flows.

## Environment and licensing

The helper sources `/apps/settings` in a private setup directory with strict
shell flags neutralized for site setup, captures setup status and logs, then
reapplies Xcelium 23.09. It preserves native return codes and serializes managed
licensed runs within a project. Temporary/cache paths are run-local. It does not
attach a GUI or modify shell/SSH/Codex configuration.

`cadex doctor --licenses` uses IC618's compatible lmutil for a read-only query.
A failed feature query is not evidence that a tool is unusable; Assura ran even
when its feature query looked unsupported. Native execution/report validation is
the deciding evidence. An ordinary VM sandbox can produce SPECTRE-209 even with
spare licenses. Request reviewed execution rather than declaring license
exhaustion, changing saved permissions, restarting servers or bypassing checks.
Legitimate Quantus QTS300 fallback after an unavailable QTS100 was observed;
inspect actual checkout/completion. No helper retries edits or tool jobs for you.

## Commands and outputs

Abbreviate `CADEX=~/.codex/scripts/cadex` in examples. A profile is selected in
cadex.json, or with invocation-only `--profile uf-gpdk180` before the subcommand.

```bash
"$CADEX" project show
"$CADEX" skill-check /absolute/job.il
"$CADEX" skill /absolute/job.il --label buffer-build
"$CADEX" netlist mylib buffer --corner NN --label buffer-netlist-NN
"$CADEX" spectre /absolute/bench.scs --label buffer-NN-27C \
  --condition corner=NN --condition temp_C=27 --source /absolute/dut.scs
"$CADEX" drc mylib buffer --label buffer-drc
"$CADEX" lvs mylib buffer --netlist-run /absolute/netlist-run --label buffer-lvs
"$CADEX" pex --lvs-run /absolute/matched-lvs-run --ground VSS --label buffer-rc
"$CADEX" psf /absolute/run/native/psf/ac.ac --axis freq --signals in out
"$CADEX" status
```

Commands return short JSON summaries and the exact unique run path. Start with
that summary and the relevant native report; select needed manifest fields
rather than loading the entire artifact inventory into context. Success requires
native completion, validated reports and unchanged inputs; completion.ok is
written only then. Explicit construction jobs retain before/after cds.lib
identities when adding a library, as described in the project format.
`engineering_acceptance` stays unassessed: verify the task-specific outputs.
Use `psf` for supported ASCII real/complex/unit-bearing operating-point data;
missing data is an error and nonfinite margin values are reported, not invented
as zero or infinite gain margin. Export selected signals with OCEAN for binary
or large results. Generated plots need actual trace/axis/window review.

## Important boundaries

- Netlisting sets `asimenv.startup/projectDir` **before** simulator selection;
  resultsDir alone does not contain OCEAN output. Unexpected outside output is
  reported, never automatically moved/deleted. Use native CDF geometry: hand-
  written wrapper defaults can produce misleading parasitics and bandwidth.
- The batch preflight catches lexical balance and lifecycle mistakes; it is
  not a SKILL compiler/type checker. Jobs return normally; the driver owns exit.
  Keep matching completion markers, especially after a native exit 0.
- `cadexPinEscape` and `cadexStub` use inspected opposing schematic pins for
  D/S, G/B and PLUS/MINUS pairs, including rotation/mirroring. They reject
  unsupported/ambiguous geometry and invalid wire creation rather than labeling
  nil. They do not implement a whole semantic component move. For new batch
  construction, load the installed `cadex-live/recipes.il` into a dynamic
  cadexCV context; check/extract and verify intended connections before saving.
- Use Assura, not the failed legacy Diva route, for this verified gpdk180
  profile. Default DRC does not include separate density/antenna checks. A zero
  Assura process status with LVS pin errors is still a failure. Internal net
  names must not accidentally become physical external-port labels.
- Current automatic CDL conversion is deliberately limited to flat native MOS
  cards. Unsupported devices/hierarchy fail clearly; preserve the established
  native CDL flow for larger designs. Do not hand-wave a missing verification step.
- PEX requires current matched LVS data. Quantus input/output directories are
  aligned in an owned working copy and its temp directory is a basename. The
  output is collected in that run, leaving previous LVS evidence intact.
- The PEX adapter supports native numeric MOS/R/C cards, preserves port order,
  connections and values, checks node-escaping collisions, uses explicit model
  mapping and omits only redundant width metadata. Unknown constructs fail;
  do not silently drop components or guess a universal PDK translation.
- Layout, simulation, geometry renders and live TigerVNC appearance establish
  different things. None permits attaching to an unapproved GUI or overriding
  another writer's lock. Existing live editing remains explicitly opt-in.
