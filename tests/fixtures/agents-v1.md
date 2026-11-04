## UF ECE and mixed-signal projects

- Run ECE commands directly on this VM. For licensed runs, use the project's configured shell, source /apps/settings in that shell, and enter the project launch directory.
- Use Xcelium 2309: after sourcing /apps/settings, run `export PATH=/apps/cds/xcelium2309/tools.lnx86/bin:/apps/cds/xcelium2309/tools/bin:$PATH` in Bash-compatible shells (or the equivalent in the project's shell). The setup script resets PATH to Xcelium 2409; reapply this override before launching tools. In Bash, `cadence_env` loads the setup and applies the override.
- Prefer the existing filelist, testbench, ADE state, and run scripts. Put project-specific launch commands, library mappings, and pass criteria in the project's AGENTS.md once verified.
- For SystemVerilog use sv-design-verification. For Verilog-A, Verilog-AMS, and analog model fidelity use vams-modeling. For simulation, results, or Virtuoso database work use cadence-virtuoso.
- Report what was actually exercised, the measured result or first actionable failure, and where I can find the run. Distinguish editor checks, elaboration, simulation, and physical verification.
