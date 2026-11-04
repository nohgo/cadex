# Live editing validation — November 3, 2026

This initial implementation record is historical. See the managed-job update
below for subsequent user-authorized live tests and current status.

Implementation and installation were performed without connecting to the user's
running Virtuoso, reading active cellviews, using TigerVNC, or acquiring a Cadence
license. The Cadex checkout is on the Mac at
`~/hardware-github/vams-suite/cadex`; source was staged under `/tmp/cadex-live-src`
on `ece-lnx-02` for independent verification. All runtime test artifacts stayed
under `/tmp`; no working Cadence project was used.

## Independent results

- **18 unlicensed tests passed** on UF ECE with Python 3.11 and SkillBridge 1.8.0.
- Installer: temporary homes, install/reinstall, user-change protection, no
  startup hooks, preserved legacy project files, generated paths, dedicated venv,
  pinned dependency, and an empty opt-in registry after installation.
- Real SkillBridge client: private socket fixtures, fragmented framing,
  short-lived reconnects, move/reverse data, closed-view model, parameter units,
  explicit save flag, nonce mismatch, stale/foreign identities, ambiguity,
  busy-session serialization, and timeout without edit resend.
- Installed helper CLI: reconnect/edit/reverse against explicitly registered
  disposable fixtures, leaving the fixture process running after disconnect.
- Real upstream SkillBridge **server and client**: the installed private-server
  wrapper exchanged requests through fake SKILL IPC and survived reconnects.
  The interpreter was a fixture; this did not execute Cadence SKILL.
- Existing batch shell smoke, missing-marker failure, and nonzero-status
  propagation passed with fake EDA executables. The maintained batch launcher
  was left byte-for-byte unchanged.
- Python syntax, SKILL parenthesis structure, skill validation, and installed
  release API signatures were checked. This is not licensed SKILL evaluation.

Actual VM Codex verification used reviewed `exec_command`, not just an ordinary
SSH Python process. The final fixture suite completed with exit 0. Its helper
CLI fixture accesses only its own temporary registration/socket, never the
production registry. Test logs and agent audit are retained under
`/tmp/cadex-live-tests.log` and `/tmp/cadex-live-agent/` on ECE.

## Installed, not activated

The one-time installation is complete, including `~/.venvs/cadex-live` and
`~/.codex/scripts/virtuoso-live`. File checks verified that the existing batch
launcher, shell startup, home `.cdsinit` presence, SSH configuration, saved Codex
permissions/configuration, and global VM instructions were unchanged. The updated
Cadence skill and runtime files match the installer manifest. Nothing was loaded
into a GUI and no production session was registered by this work.

**Only later, when the user chooses to enable the intended GUI**, this is the
single CIW action with installed paths:

```lisp
load("/home/UFAD/nohgoering/.codex/share/cadex-live/bootstrap.il")
```

The helper command `~/.codex/scripts/virtuoso-live attach-command` prints it.
Use `virtuoso-live status` and `virtuoso-live run /absolute/path/to/job.json` on
the GUI host afterward, or give VM Codex a named live-edit request. The skill
routes explicitly connected GUI edits through per-command reviewed execution.

## Pending licensed/database and visual acceptance

**Real database verification and live visual verification remain pending.** No
spare-license/resource guarantee was available while the user was actively
working, so no disposable licensed Virtuoso or real batch smoke was started.
Prior batch success is historical evidence, not a fresh licensed test here.

Later, after opting in, use only scratch copies made through normal Virtuoso
operations. Inspect a named instance in an already-open scratch view, record its
origin, and move it +1 user unit in X with Y unchanged (`save: false`). In
TigerVNC, confirm exactly that named instance moves and no editor closes. Reverse
it with a fresh client using the read-back original coordinates. Then target a
second existing scratch view that is closed: confirm it opens in the same GUI,
the named instance changes visibly, a fresh client reverses it, and the GUI stays
open. Test typo and write-lock refusal with scratch targets. Test PDK parameter
callbacks only after geometry acceptance succeeds. Numeric fixture results do
not substitute for these real database/window checks.

## API references consulted

- [SkillBridge project and API](https://github.com/unihd-cag/skillbridge)
- [SkillBridge communication protocol](https://unihd-cag.github.io/skillbridge/reference/protocol.html)
- Installed IC618 references: `doc/skdfref/chap3.html` (`deOpenCellView`),
  `doc/skuiref/chap9.html` (`hiRedraw`), `doc/skdfref/cvio.html` (reference-count
  behavior; the live backend deliberately avoids `dbClose`).
- [Cadence CDF setter guidance](https://community.cadence.com/cadence_technology_forums/f/custom-ic-design/56702/modify-pcell-parameter-due-to-skill-code)

## Managed-job update

Source remains in the Mac Cadex Git checkout; generated jobs and audit records
now belong under `~/.local/state/cadex/live/{jobs,runs}`, not the Cadence project.
The main skill routes circuit editing and simulation to separate references.
Maintained transport/context/API recipes replace per-task Python bridge glue.

**24 independent tests passed** on ECE with Python 3.11 and SkillBridge 1.8.0.
The six additional managed-job cases exercise private job creation, verified API
lookup and invented-API refusal, lifecycle/save glue rejection, identity/audit
contracts, failure records without completion markers, and installed CLI usage
against disposable fixtures. This verifies transport/installation contracts,
not the execution of checker gates by a licensed SKILL interpreter.

The managed schematic path checks baseline errors, refuses saving pre-existing
unsaved edits without explicit authorization, checks after the job, verifies
declared net/terminal assertions, saves, and returns a post-check/save snapshot.
Its actual Cadence behavior is exercised separately by the raw task below.

No GUI is contacted during implementation/fixture testing. Existing opted-in
GUI attachment, batch launcher, bootstrap, startup and permission settings are
preserved during deployment. Visual verification still requires the user.

### Raw cascode test through a fresh VM Codex session

Prompt (complete, with no follow-up guidance):

> Turn the circuit in tut2/part3_param into a cascode.

Session: `01a1a4c9-b8f6-7880-943e-f50fb5d23346`. The agent discovered the
installed skill and references itself. All commands completed successfully; it
did not reconstruct Python transport, guess missing APIs, or require manual
correction. Every live-helper call requested `require_escalated` on the first
attempt, using `~/cadence_work` as workdir and operation-specific justification.
Automatic per-command review completed without requesting user interaction.
No additional instruction was sent to this session after the initial task.

The job created a matching `gpdk180/nmos` NM1 above NM0, with both devices
W=2u/L=180n/m=1. Saved readback verified NM0.D=NM1.S, original V0=vgs at
NM0.G, new V1=vcas at NM1.G, and NM0.S, both bulks and both voltage-source negative terminals on gnd!. NM1.D remains an open output, consistent with the
original open-drain test circuit. The checker reported **0 errors/1 warning**
before and after; updateConn, runSRC and runVIC were all enabled. `dbSave`
succeeded, post-save modified state was nil, status was 0 and completion.ok
was present. There were eight instances after the change.

No electrical simulation or operating-point validation was performed; `vcas`
is an expression requiring an appropriate testbench value. The agent's own
final response identified the open output and pending visual review.
**Database verification passed; live visual/readability verification remains
pending user observation in TigerVNC.** No screenshots or window focus actions
were used. No separate Virtuoso process or license was started.

VM-local records (not committed; no private database or nonce in this source):

- Agent prompt/events/final: `~/.local/state/cadex/live/agent-tests/cascode-raw.lG9clm/`
- Submitted job/checks/post-save snapshot: `~/.local/state/cadex/live/runs/20261104T042145Z_job_e2_f2xzl/`
- Generated job: `~/.local/state/cadex/live/jobs/20261104T042124Z_part3-param-cascode_hry5o4qn/`

The seven known helper/report files from the preceding gate-source test were
archived from `~/cadence_work/runs/part3_gate_source` into
`~/.local/state/cadex/live/history/part3_gate_source_20261104T042018Z/`.
The new test wrote no tooling artifacts into the Cadence project. Maintained
source, installer, recipes, tests and instructions are tracked on the Cadex
`codex/live-circuit-jobs` branch.
