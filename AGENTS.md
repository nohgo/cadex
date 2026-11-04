## UF ECE and mixed-signal projects

- Run ECE commands directly on this VM. For licensed runs, use the project's configured shell, source /apps/settings in that shell, and enter the project launch directory.
- Use Xcelium 2309: after sourcing /apps/settings, run `export PATH=/apps/cds/xcelium2309/tools.lnx86/bin:/apps/cds/xcelium2309/tools/bin:$PATH` in Bash-compatible shells (or the equivalent in the project's shell). The setup script resets PATH to Xcelium 2409; reapply this override before launching tools. In Bash, `cadence_env` loads the setup and applies the override.
- Prefer the existing filelist, testbench, ADE state, and run scripts. Put project-specific launch commands, library mappings, and pass criteria in the project's AGENTS.md once verified.
- For analog circuit topology, sizing, bias and loads use analog-design; for an end-to-end requested outcome use analog-design-flow. Use cadence-simulation for testbench design, simulation and measured results; cadence-layout for layout and physical checks; cadence-virtuoso for live/batch database operations, named edits and checked saves. Read the relevant skill as the task reaches that stage.
- For SystemVerilog use sv-design-verification. For Verilog-A, Verilog-AMS, and analog model fidelity use vams-modeling.
- Report what was actually exercised, the measured result or first actionable failure, and where I can find the run. Distinguish editor checks, elaboration, simulation, and physical verification.

- For configured project paths and labeled native-tool runs, use ~/.codex/scripts/cadex project show and the relevant Cadex skill. Preserve existing project organization and normal Cadence startup; do not automatically migrate a working project.
