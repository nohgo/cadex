---
name: cadence-virtuoso
description: Run UF ECE Cadence simulations, diagnose logs, extract ADE results, or inspect and edit Virtuoso schematics and layouts through SKILL or SkillBridge.
---

## Virtuoso on this VM

**VM Codex: request per-command review on the first launcher attempt.** For `bash ~/.codex/scripts/virtuoso-batch.sh path/to/job.il`, set the execution tool's `workdir` to the actual Cadence project directory containing `cds.lib` and set `sandbox_permissions="require_escalated"` on the first invocation. The ordinary VM Codex sandbox failed; reviewed per-command execution succeeded. Do not spend an attempt in the ordinary sandbox or hand the command back to the user when the reviewed execution tool is available.

The review justification must identify the actual project and the operation the job performs, for example: `Read tut_1/inverter/schematic in ~/cadence_work and report instance and net counts.` Group related SKILL operations for one design change into one job and one launcher invocation. This first-attempt review instruction applies specifically to the Virtuoso launcher; it is not a blanket escalation rule for other commands.

After the process finishes, check its exit status, the unique `completion.ok` marker in the printed RUN directory, and task-specific output such as the named cellview and measured counts. A zero CLI/session exit alone is insufficient. If review denies the command, stop and report the stated reason; do not bypass review through another command or change saved permissions. Keep per-command review in place. If the execution tool cannot request review, report that limitation.

VM-local command (generic smoke test, run in the intended project):

```bash
cd ~/cadence_work && bash ~/.codex/scripts/virtuoso-batch.sh
```

The invocation directory is the project root. Add a job argument, e.g. `bash ~/.codex/scripts/virtuoso-batch.sh path/to/job.il`; relative job paths resolve from that project. From any directory, select another project with `bash ~/.codex/scripts/virtuoso-batch.sh --project ~/ams-test path/to/job.il`. A readable project `cds.lib` is required before setup. The no-argument smoke checks SKILL execution and library discovery without assuming any project cell exists.

Classify by purpose before launch. Circuit design, measurement and debugging jobs belong in the default `<project>/runs/`, even on failure. The built-in no-job smoke test writes to `~/.local/state/codex/virtuoso/` automatically. Pass `--diagnostic` for a custom tooling check (launcher, permissions, license access, database access); keep its supporting probe files in the diagnostics area as well. For circuit jobs, write exports under the printed RUN directory using CODEX_VIRTUOSO_RUN. Preserve historical scratch_runs directories.

For the separate, read-only tut_1 inverter tooling check in cadence_work:

```bash
cd ~/cadence_work && bash ~/.codex/scripts/virtuoso-batch.sh --diagnostic ~/.agents/skills/cadence-virtuoso/examples/tut1-inverter.il
```

The launcher handles scratch-isolated site setup, the Xcelium 23.09 override, normal project initialization, a private authenticated display, timeout, and teardown. Let jobs return normally and raise errors on failed checks. Ordinary-shell success and VM-agent success are separate results. The previously tested VM Codex sandbox blocked startup, including X-server socket binds; relocating the launcher does not grant that permission. Use the reviewed launcher path above from VM Codex. Existing Spectre decks and Xcelium benches use their normal batch commands.

### Establish context

Run directly in the ECE project environment. Identify the actual execution host, project launch directory, setup shell, cds.lib or project mapping, DUT and test. Load /apps/settings in the same compatible shell as the tool. Prefer the saved launch procedure for projects needing additional PDK setup. Confirm the needed executable resolves. A login host and the host running Virtuoso may differ.

### Choose the testbench

Preserve the DUT schematic as the source of device connectivity. Reuse a working ADE bench or config when one exists. For new regressions, prefer a text bench: instantiate a freshly netlisted DUT subcircuit with the exact generated port order, models, section and global supplies. For a pulse, load or parameter sweep, native Spectre sources suffice. Use Verilog-A for reusable electrical stimulus; use SV plus Verilog-AMS when digital sequencing/checking interacts with analog behavior. Keep a small schematic top when ADE view switching, interactive inspection or a required schematic deliverable makes it worthwhile. Inspect the device/tutorial setup before selecting VDD. For scratch work on an existing design, checksum the original cell design files before and after.

### Run and measure

Reuse the known-good test command or ADE-generated run procedure. For pure SV use the project's Xcelium filelist and top. For electrical simulation replay the Spectre deck with its original include resolution, model section, analyses and save options. For mixed-signal runs preserve the config view, AMS elaboration, connect modules and analog solver setup. Regenerate a netlist after a schematic or binding change. Replaying an old input.scs cannot verify a new schematic.

Use a fresh run directory or the project's supported output override; preserve relative input paths and previous runs. Capture exact invocation, tool version, top/config, corner, variables and seed as applicable. Keep simulator exit status even when logging through a pipe. Read compile, elaboration and solver logs in order, then inspect assertion or measurement output. Report the first causal diagnostic with context. Distinguish license/setup failures, convergence failures and DUT failures.

Use OCEAN or the project's ADE export to read the matching results directory, analysis, sweep point and signal. Export named scalar measurements with units; export a waveform window when it explains a discrepancy. Record threshold, edge, time window and expected tolerance. Missing data or a missing test completion marker is inconclusive.

For OCEAN inside a Virtuoso batch job, use normal autoloading via `simulator('spectre)`; avoid constructing a release-specific ocean.cxt path. Verify both the ADE simulation workspace and results directory. Locate the actual generated netlist and archive it with the run, preserving the original include-resolution context for replay. `resultsDir` alone does not locate the netlist.

For a requested transient plot, require the following evidence:

1. Inspect the fresh netlist for DUT pin order and intended input, output, supply, bulk and load connections. For schematic benches draw wires at transformed symbol pins and label the intended nodes before Check and Save. Database net and instance-terminal objects alone can lose connectivity during checking.
2. Verify the transient reached the requested stop time. If an ADE log reports completion followed by SIGTERM/errors, retain that log and replay the same generated deck using its standalone Spectre command to resolve ambiguity. Preserve checkout diagnostics if a sandbox run cannot reach the license server; request reviewed execution for that specific replay when permitted.
3. Inspect numeric data for the named signals, finite samples and requested events (both input edges for a rise/fall test). Check the observed DUT response against the expectation and report a mismatch as a test failure. Open or render the exported PNG and verify the traces, labels and time window; a launcher marker only verifies job completion.
4. Return the plot path, run directory and any original-cell checksum comparison.

### Work with a live cellview

Use a named SkillBridge session and run its Python client under the same user on the same host as Virtuoso. Use one client at a time. First query library, cell, view and instances. Resolve every write against an explicitly named destination. Inspect a known-good PDK device for master, terminal names, CDF parameter names/types, units and callback behavior. Read the installed release's SKILL help when a database call or argument is uncertain.

For schematic generation, start in a new work cell or copy. Place instances by master, transform actual symbol pin locations before creating wires, and check connectivity by terminal-to-net mapping, including bulk. Run Check and Save, regenerate the netlist, compare devices and connections against intent, then run the smoke bench. On retry inspect the partial result before adding objects.

For layout, start with one known PCell in a scratch cell. Inspect evaluated dimensions, orientation, pin shapes, grid, layer-purpose pairs and legal vias. Place and route a small block against its schematic. Inspect extracted connectivity; run the project's DRC and LVS decks and distinguish each result. Include parasitic extraction and post-layout simulation when the requested result concerns circuit performance. Never edit PDK masters or manipulate OpenAccess files with a text editor.

### VM runbook

**Environment.** In Bash, use the site's `cadence_env` if defined. Otherwise run the following in the shell that will actually launch the tool. Repeat for each fresh shell. Run from the project's normal launch directory so its library and PDK configuration resolve.

```bash
source /apps/settings &&
export PATH="/apps/cds/xcelium2309/tools.lnx86/bin:/apps/cds/xcelium2309/tools/bin:$PATH" &&
command -v virtuoso spectre ocean xrun &&
xrun -version
```

Confirm Xcelium 23.09 for Xcelium tasks. Source any project-specific setup in the order used by the known-good project launcher. Start a new Virtuoso GUI only in a graphical session when needed.

**Build the right artifact.** Inspect the Makefile, launch script, filelist and generated ADE run command before constructing a new command. Preserve the working directory used to resolve relative paths. Keep build products separate using project-supported options.

| Input | Build and validate |
|---|---|
| SV RTL and testbench | Run the project's target. For standalone SV, the template is `xrun -sv -f files.f -top tb_top -l xrun.log`. Supply the actual filelist and top module name. Order packages before imports, compile each translation unit once, and pass header directories with `+incdir+...`. Preserve defines, libraries, timescale and seed from the project. Inspect compile, elaborate, and run stages plus a self-checking result. |
| Spectre with Verilog-A | Use the ADE netlister or a standalone Spectre test deck containing an `ahdl_include` for the model and an instance with the correct terminal order. Start from the generated simulator invocation or, for a self-contained bench, `spectre input.scs` in its intended run directory. Verify AHDL compilation, successful analysis, and measured response. |
| SV plus electrical Verilog-AMS | Use the project's AMS Designer config and generated Xcelium/Spectre launcher. Re-netlist after source-view or schematic changes and inspect elaboration for the bound views, disciplines and connect modules. A standalone digital filelist cannot reproduce this setup. |
| Schematic or layout | Use Virtuoso database APIs and the cellview checks above. For layout use the project's technology-specific streams and verification runsets only when the deliverable requires them. |

**Choose the execution path.** Run file-based stimulus generation, existing netlisted simulations, log analysis and waveform export in batch. A live session is required only when the selected operation depends on Virtuoso application APIs or live state. If an independent batch check can proceed while schematic generation is blocked, run it and label its input provenance.

Use the launcher above from the intended project directory, or select it with `--project DIR`. Establish its library mappings before launching. A one-shot SKILL replay may be sufficient. Start SkillBridge only when the requested operation benefits from a persistent interactive connection, in a dedicated session owned by the launcher. Keep ordinary Virtuoso startup and .cdsinit untouched. Verify the launcher by opening a named library/cell/view from a fresh execution shell, record the verified invocation, and release its own processes and licenses when finished. The CIW steps below are for an explicitly requested attachment to an existing GUI.

**Connect Python to a live GUI.** On the Virtuoso host, check for an existing working venv first. For first-time setup in Bash:

```bash
venv_dir="$HOME/.venvs/skillbridge"
if [ ! -x "$venv_dir/bin/python" ]; then python3 -m venv "$venv_dir"; fi
"$venv_dir/bin/python" -m pip install skillbridge
"$venv_dir/bin/skillbridge" path
printf '%s\n' "$venv_dir/bin/python"
```

In that Virtuoso window's CIW load the printed .il path, then start the named session with the printed absolute interpreter path. If the agent has only a terminal and no working bridge, give these two lines with the actual paths to the person at the CIW. A pip install alone does not attach a running GUI.

```lisp
load("/absolute/path/from/skillbridge/path")
pyStartServer ?id "codex" ?python "/absolute/venv/bin/python"
```

Open the target cellview. From the same account and host, run the following before any edit. If no edit view exists, request or explicitly open the target. If the server times out mid-edit, inspect the partial state after restarting the bridge before retrying.

```bash
"$HOME/.venvs/skillbridge/bin/python" - <<'PY'
from skillbridge import Workspace
cv = Workspace.open("codex").ge.get_edit_cell_view()
if cv is None:
    raise SystemExit("Open the intended cellview in Virtuoso.")
print(cv.lib_name, cv.cell_name, cv.view_name)
PY
```

**Inspect and deliver waveforms.** For analog results use ViVA in ADE or OCEAN headlessly. For an individual transient sweep point, adapt the following to actual paths and signal names. Run it with the site's OCEAN batch invocation (commonly `ocean -nograph -restore export.ocn`). Inspect `results()` and `outputs()` to resolve names. Select the intended corner and sweep member before exporting.

```lisp
openResults("/absolute/path/to/run/psf")
selectResult('tran)
ocnPrint(?output "/absolute/path/to/run/vout.txt" ?numberNotation 'scientific getData("/vout"))
exit()
```

For Xcelium digital results, open the existing SHM database in SimVision (`simvision waves.shm` in a graphical session). If the signals were never saved, rerun with scoped probes. For example, pass `-input waves.tcl` to the normal xrun command and put the following in waves.tcl, substituting the actual scope. Enable the required read access during elaboration if internal probes are unavailable.

```tcl
database -open waves -into waves.shm -default
probe -create tb_top -database waves -all -depth 1
run
exit
```

When asked to show a trace, deliver a readable PNG plus numeric data if requested. For analog, inspect the exported table's headers and numeric rows, then plot it using an available headless plotting tool (e.g. Matplotlib Agg). If NumPy/Matplotlib are unavailable, parse the table with standard-library Python, write a labeled SVG, and use installed ImageMagick (e.g. `convert waveform.svg waveform.png`). For digital, use an actual SimVision waveform export or a VCD dump of the requested signals rendered with stepped transitions and X/Z preserved. Verify the exported time interval, units, signal names, sample count and image readability. Keep the original PSF/SHM on ECE and identify its run. From a Mac-side agent, retrieve the finished files using the ece alias (e.g. `scp ece:/absolute/run/vout.png ./vout.png`, with a real local destination) and attach or link the local image. From VM-only Codex, report the exact remote paths and a ready-to-run Mac retrieval command when attachment is unavailable. Do not claim a remote path was delivered as an image.
