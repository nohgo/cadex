# Cadex

A Cadence setup for Codex on UF ECE Linux. Cadex installs three Codex CLI skills and an on-demand Virtuoso batch launcher. Use it to write SV and Verilog-AMS, run simulations, and inspect or edit Virtuoso cellviews from a project terminal.

| Skill | Use |
| --- | --- |
| `sv-design-verification` | Write RTL and self-checking SystemVerilog benches, then verify them with the project filelist. |
| `vams-modeling` | Choose between RNM, Verilog-A, and Verilog-AMS and check a model against its intended behavior. |
| `cadence-virtuoso` | Run Spectre/Xcelium benches, extract waveforms, and run SKILL jobs against Virtuoso. |

## Install

The target is a Linux account with Python 3.6+, Bash, Codex CLI, and access to the UF Cadence tools and licenses. The launcher uses the site's `/apps/settings`, Xcelium 23.09 installation, GNU `timeout`, and Virtuoso's `-nograph` wrapper. Projects need a readable `cds.lib`. SkillBridge is optional for live GUI interaction.

**From a Mac with the repository checked out**, open a terminal in the repository root. The installer uses the existing multiplexed `ece` SSH alias. If its master connection is inactive, connect to the campus network or VPN and authenticate with `ssh -fN ece` first.

```bash
sh install-on-ece.sh
```

**From an existing checkout on the VM**, run this in the repository root instead:

```bash
python3 install.py
```

Re-run the same installer after updating the checkout. It copies the skills to `~/.agents/skills/`, installs `~/.codex/scripts/virtuoso-batch.sh`, and merges the VM instructions into `$CODEX_HOME/AGENTS.md` (default `~/.codex/AGENTS.md`). Upgrades back up replaced files under `~/.codex/ece-install-backups/` and stop on unrecognized local changes. Installation adds no SSH or Virtuoso startup hook.

## Verify and use

In an ordinary VM shell, select a Cadence project and run the no-argument smoke test. It starts Virtuoso, enumerates the project's libraries, and exits.

```bash
cd ~/cadence_work  # or another directory containing cds.lib
bash ~/.codex/scripts/virtuoso-batch.sh
```

Look for `STATUS=0`, a completion marker, and a library count. For a custom job, provide a SKILL file relative to the project or use an absolute path. Have the job return normally so the launcher can record completion.

```bash
bash ~/.codex/scripts/virtuoso-batch.sh path/to/job.il
bash ~/.codex/scripts/virtuoso-batch.sh --project ~/ams-test path/to/job.il
```

Circuit jobs keep their logs and outputs in the project's `runs/`. Smoke tests and custom probes marked `--diagnostic` go under `~/.local/state/codex/virtuoso/`. Each launch prints its exact output directory as `RUN=`.

For an interactive VM Codex session, start in the project directory:

```bash
codex --approve-for-me
```

Use `/skills` to verify discovery. Then try “Read the inverter schematic and report the devices and nets.” The VM skill directs Codex to request review for a Virtuoso launch because the ordinary workspace sandbox can block licensing or the private display. Existing netlisted Spectre and digital Xcelium benches use their own project commands.

## Repository layout

- `skills/` contains the three skill definitions and the optional UF tutorial inverter example.
- `scripts/virtuoso-batch.sh` is the Linux launcher.
- `AGENTS.md` contains the instructions installed for VM Codex.
- `install.py` performs the Linux installation. `install-on-ece.sh` transfers the same bundle over SSH from macOS.

## Opt-in live editing in TigerVNC

Install the optional, pinned SkillBridge 1.8.0 dependency once (Python 3.8+;
UF provides Python 3.11). From the Mac:

```bash
sh install-on-ece.sh --live
```

Or in a VM checkout: `python3 install.py --live`. This uses the dedicated
`~/.venvs/cadex-live` venv and installs `~/.codex/scripts/virtuoso-live` plus
`~/.codex/share/cadex-live/`. It does **not** find a GUI, acquire a license,
connect to a running process, or change `.cdsinit`, startup, SSH, or saved Codex
permissions. A running Virtuoso alone is never authorization to connect.

**Later, when you choose to enable the intended GUI**, get the exact CIW action:

```bash
~/.codex/scripts/virtuoso-live attach-command
```

The installed default is this single CIW command (with your home expanded by the
installer):

```lisp
load("/home/UFAD/nohgoering/.codex/share/cadex-live/bootstrap.il")
```

Do this once per GUI session. It starts a named, private, local SkillBridge
endpoint in that GUI and records explicit consent. It refuses to replace an
existing SkillBridge server. No batch driver is loaded. Logs and registrations
stay in `~/.local/state/cadex/live/`, outside Cadence projects. Loading the
bootstrap is activation; simply installing files or running status is not.

Day to day, give VM Codex the circuit task by library/cell/view and object name.
It discovers the installed skill, uses reviewed execution, and plans the local
circuit change including attached wires, grounds and labels. Completed schematic
edits normally run checking, verify connections/readability and save. Explicit
previews remain unsaved; saving unrelated pending work requires authorization.

The managed entrypoint handles Python, reconnection, target identity, locking,
check/save and audit output. Its commands are also usable directly:

```bash
LIVE=~/.codex/scripts/virtuoso-live
"$LIVE" status
"$LIVE" inspect --library my_lib --cell my_cell --view schematic
"$LIVE" new-job --name local-edit
# Fill the returned job.il with circuit operations using the managed recipes.
"$LIVE" skill /absolute/returned/job.il --library my_lib --cell my_cell --view schematic --save
"$LIVE" api dbFindOpenCellViewByName
```

Use the same ECE host/account as the GUI. Multiple registrations require an
explicit `--session`; stale/foreign sessions are not silently ignored. Status
reads metadata only. Clients verify host/account/PID start times, socket peer,
and session nonce, and serialize requests. A completed client disconnects while
the GUI stays open. No automatic retry or bootstrap reload occurs.

The existing low-level JSON `run` interface remains available for isolated
instance operations. A raw origin move does not stretch schematic wiring;
prefer managed jobs for circuit changes. Its `save:true` only writes the DB,
whereas managed schematic `--save` gates saving on checks and declared
connection assertions. Managed layout check/save is not implemented.

See [managed jobs and recipes](skills/cadence-virtuoso/references/live-jobs.md)
and [circuit-aware editing](skills/cadence-virtuoso/references/circuit-editing.md).
The managed code loads only namespaced job/recipe definitions into the opted-in
GUI. It never loads the batch driver, which calls `exit()`.

### Keep source and runtime artifacts separate

| Location | Contents |
| --- | --- |
| Cadex Git: `live/`, `skills/`, `tests/`, `docs/` | Maintained helpers, SKILL recipes, instructions and independent tests. |
| `~/.codex/share/cadex-live/`, `~/.codex/scripts/` | Installer-managed runtime copies. Change source, then reinstall. |
| `~/.local/state/cadex/live/jobs/` | Generated per-task SKILL source (`new-job`). |
| `~/.local/state/cadex/live/runs/` | Submitted code copies, requests, status and result/failure reports. |
| `~/.local/state/cadex/live/sessions/` | Private opt-in registrations; never commit. |
| Cadence project | Design files and intentional circuit/simulation deliverables; no live bridge glue. |

Upgrading installation leaves an existing GUI attachment unchanged. No startup,
SSH or saved Codex permission settings are changed. Edit jobs are trusted SKILL
reviewed per command, with guardrails against accidental lifecycle/batch glue;
they are not an in-process security sandbox.

### Independent verification and deferred visual acceptance

Run the **unlicensed** tests from a VM source checkout using the live venv:

```bash
~/.venvs/cadex-live/bin/python -m unittest discover -s tests -v
```

These use temporary homes and explicitly created socket fixtures with the real
SkillBridge Python client. They are not Cadence database or visual verification.
No test discovers an arbitrary Virtuoso, contacts the user's GUI, or reads their
cellviews. The batch launcher remains independent. The batch shell harness uses
fake tool executables; a licensed smoke run must be deferred whenever resources
or license availability for the user's session are uncertain.

Real database/visual acceptance requires an explicitly opted-in session. Later,
use a scratch library/cell copied through normal Virtuoso tools, not your working
design. Keep the scratch view open and inspect a named instance's origin. Move
it by a clearly visible +1 user unit in X using an expected-origin guard; confirm
in TigerVNC that exactly that instance moved and no window was closed. Run a
reverse job from a fresh client, using the reported original coordinates. Then
target a second existing scratch view that is closed: confirm it opens in the
same GUI and the named instance moves. Reverse it from another client and
confirm the GUI stays open. Keep `save: false` throughout. This verifies the
visible GUI behavior; numeric readback alone does not.

The bootstrap/backend SKILL must be validated against the installed Cadence
release and the specific PDK callbacks before relying on live edits. In
particular, do the scratch geometry acceptance before parameter/callback edits.

See [the validation record](docs/live-validation.md) for independent results and the deferred licensed/visual checks.
