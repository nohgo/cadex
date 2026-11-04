# Simulation, batch environment, and result verification

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

Use the launcher above from the intended project directory, or select it with `--project DIR`. Establish its library mappings before launching. A one-shot SKILL replay may be sufficient. Use the opt-in live helper for a user-connected editor. Do not start another Virtuoso or SkillBridge process merely because an existing GUI is visible. Keep ordinary Virtuoso startup and .cdsinit untouched. Verify the launcher by opening a named library/cell/view from a fresh execution shell, record the verified invocation, and release its own processes and licenses when finished. The CIW steps below are for an explicitly requested attachment to an existing GUI.

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
