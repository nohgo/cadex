---
name: cadence-virtuoso
description: Inspect and edit named Virtuoso schematic/layout objects, execute reviewed live or batch SKILL jobs, and handle GUI connections, checking, saving and API mechanics on UF ECE.
---

## Choose the workflow

- **Named schematic/layout edits:** read [Circuit-aware editing](references/circuit-editing.md) and [Managed live jobs](references/live-jobs.md). Use an explicitly connected GUI by default. Preserve circuit intent, attached local geometry, readable spacing/labels, and the intended save state.
- **Circuit engineering:** use [analog-design](../analog-design/SKILL.md) for topology, bias, load and sizing decisions. For a multi-stage outcome use [analog-design-flow](../analog-design-flow/SKILL.md).
- **Testbenches, simulation and measurements:** use [cadence-simulation](../cadence-simulation/SKILL.md); keep existing regression behavior. For layout engineering/physical checks use [cadence-layout](../cadence-layout/SKILL.md).
- **No live registration:** use the reviewed batch launcher for ordinary saved work. If the user explicitly wants to see the edit live, report the missing connection and print the command from `virtuoso-live attach-command`; do not substitute a hidden batch edit.

## Live execution

Use the installed `~/.codex/scripts/virtuoso-live` entrypoint. It selects the dedicated Python environment and manages host/session identity, locking, named-view lookup, audit output, and check/save. Do not reconstruct bridge/Python glue or choose a bare python3 interpreter for live jobs.

1. Run `virtuoso-live status`. This reads opt-in registration/process/socket metadata only. A running Virtuoso process alone is never permission to connect. Honor current user restrictions even if a registration exists. Multiple/stale/foreign sessions require an explicit resolution; never choose an arbitrary GUI.
2. Run `virtuoso-live inspect --library LIB --cell CELL --view schematic` for the named target's instances, CDF values, transformed pins, connections and wire geometry. Do not guess names or read the selected cellview instead.
3. Create tooling work with `virtuoso-live new-job --name short-description`. Fill the returned job.il using the managed context and verified recipes. Execute it with `virtuoso-live skill /absolute/job.il --library LIB --cell CELL --view schematic --save` for a completed authorized edit. Use an unsaved preview only when requested. See the guide for pre-existing unsaved edits and --allow-existing-edits authorization.
4. Check exit status, completion.ok, actual task output, baseline/final error and warning counts, connection assertions, saved status and readability. An exit code alone is insufficient. A failed job can leave partial edits: inspect before retrying. Never close/discard the user's editor.

For **every live-helper or Virtuoso batch-launcher invocation**, request reviewed execution on the first attempt: set tool `workdir` to the actual project containing cds.lib, `sandbox_permissions="require_escalated"`, and a justification identifying the project and exact operation. Keep per-command review; report a denial without bypassing it or changing saved permissions. File inspection and unrelated tools do not inherit blanket escalation.

## Reuse verified mechanics

Before a custom SKILL call, consult `virtuoso-live api FUNCTION` or the [verified API recipes](references/live-jobs.md). Prefer recipes. If the installed release's function/signature is unfamiliar, look it up rather than inventing it. Mechanical API errors should not require user guidance. Make one coherent job for a design change, and verify the result before another edit.

Keep reusable helpers/recipes/tests in the Cadex Git repository. The installer deploys copies under ~/.codex and ~/.agents. Generated jobs, copied submitted code, logs and reports belong under ~/.local/state/cadex/live/{jobs,runs}; use new-job instead of creating bridge scripts in the Cadence project. Circuit deliverables intentionally requested by the user may use the project's runs area. Do not copy PDK/vendor code, session tokens, generated binaries or private design databases into Cadex Git.

## Batch execution

VM-local generic smoke (no GUI attachment):

```bash
cd ~/cadence_work && bash ~/.codex/scripts/virtuoso-batch.sh
```

Supply a project-relative or absolute job.il for ordinary batch work. The launcher requires cds.lib before setup, isolates /apps/settings setup, reapplies Xcelium 23.09, preserves normal project initialization, manages its own private display and timeout, and prints RUN. Verify native status, completion.ok and task-specific output. Circuit jobs use <project>/runs; no-job smoke and --diagnostic tooling probes use ~/.local/state/codex/virtuoso. Preserve historical runs. Never load a batch driver into a GUI: it calls exit().

## Session lifecycle

Installation does not attach, reload, detach or replace a GUI/server. Only the user's chosen one-time CIW bootstrap opts in that GUI. Do not ask for CIW actions while the user says they are working. Managed jobs load only Cadex's namespaced recipes in the already authorized connection; they never restart the bridge. Do not force write locks, alter startup/SSH settings or persist broader permissions. Source /apps/settings only for actual licensed batch tools; live jobs use their GUI's existing environment.
