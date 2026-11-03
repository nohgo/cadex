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
