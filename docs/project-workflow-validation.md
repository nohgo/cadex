# Project workflow implementation and validation — 2026-11-04

This change follows the [full FVF test](full-tests/2026-11-04-fvf.md).
That test eventually completed the tool flow, but repeated environment,
netlisting, licensing diagnostics and format translation were avoidable agent
work. Successful tool execution also did not erase its bias-range and stability
limitations. The fix separates reusable execution mechanics, project evidence,
and engineering acceptance.

## Structure and agent design

The UF reference was `~/asar_adc_8bit`, observed as a root with `cadence/`,
`sar-adc-rtl/`, `stimulus/`, `synth/` and `pictures/`. Only directory structure
and root documentation were inspected; no SAR database was opened or changed.
Cadex preserves existing names, nested RTL repositories and startup files.
New full projects add `cadex.json`, a Cadence launch directory, separate
results, `agent/{designs,notes,work}`, and native `.agents/skills/` discovery.
Small projects keep Cadence at the root; unconfigured cds.lib directories work
without scaffolding and put managed output in private Cadex state.

Seven top-level skills remain. Conditional detail lives in focused references;
fragile repeatable operations live in the installed `cadex` CLI. No worker
framework, mandatory delegation, startup hook or saved permission was added.
This applies the scoped discovery, progressive disclosure and executable-helper
guidance in [OpenAI's skill documentation](https://developers.openai.com/plugins/build/skills).
The realistic forward test below checks instruction discovery as well as unit
behavior. Source belongs in Cadex Git; private jobs, vendor files, cellviews,
registrations and raw native results do not.

## Friction addressed

| Observed failure or risk | Implemented response |
| --- | --- |
| Site setup copies files and breaks strict shell flags | Private setup directory, neutralized flags during sourcing, captured status/logs, Xcelium 23.09 reapplied. |
| License queries misdiagnosed tools; sandbox produced SPECTRE-209 | Compatible IC618 lmutil for optional read-only diagnostics; actual native execution decides availability; reviewed execution on the first licensed call. |
| Diva failed; Assura RCX is retired | Bounded verified Assura DRC/LVS and Quantus 22.1 profile, without changing servers or bypassing licenses. |
| OCEAN wrote outside the intended results directory | Set projectDir before simulator selection; verify containment, retain unexpected-output failures. |
| Handwritten device defaults distorted simulation | Fresh native saved-schematic netlist and explicit source/dependency identities. |
| Repeated pin-direction and nil-wire mistakes | Inspected opposing-pin geometry helpers for rotation/mirroring, checked wire creation, post-check connectivity assertions. |
| Native return 0 confused with verification success | Native termination, DRC totals, positive LVS match, markers and source freshness checked separately. |
| Extraction changed old evidence or wrote to cwd | Owned copy of matched LVS, matching Quantus directories, basename scratch directory, owned working directory. |
| Manual PEX conversion and incomplete PSF parsing | Strict bounded adapters with explicit model/port mapping and collision rejection; real/complex/unit-bearing PSF values. |
| Output and agent probes mixed with Cadence work | Unique labeled runs, ignored scratch, maintained helpers in Git, concise CLI summaries. |
| Passing tool flow masked electrical shortcomings | Separate engineering acceptance, preserved failed assumptions, operating-point/headroom and metric checks in stage guidance. |

## Independent tests

The final ECE Python suite passed **52 tests** (23 new workflow tests plus 29 existing
installer/live/batch tests), using temporary homes, fake tools and explicit
socket fixtures. These tests cover full/small/legacy discovery, SAR-shaped
adoption preserving source/startup/locks, path containment, installer conflicts,
unique runs, stale/tampered dependencies, run serialization, setup failure,
owned-process timeout cleanup, false-success DRC/LVS, isolated extraction,
unsupported format rejection, PSF values and lexical SKILL preflight.
The seven installed skills also pass frontmatter validation. The validator's
PyYAML dependency was installed only in a temporary Mac validation venv.

Licensed native regression used only a newly regenerated private fixture:

```text
~/.local/state/cadex/framework-tests/native_1tbnu1_9/chip/
```

The fixture library `cadex_fixture` was regenerated from the prior test's
construction scripts. It did not copy or open the user's active cellviews.
Every managed output below is under this fixture's `results/`; native ADE
netlisting stayed there rather than in `~/simulation`.

| Actual operation | Result / run beneath results/ |
| --- | --- |
| Batch schematic/layout construction | Completed with markers; library-mapping before/after hashes retained. |
| Fresh native schematic netlist | Contained; IN OUT VDD VSS IBIAS; `netlist/buffer-netlist-NN/20261104T174048Z_9htsosf3`. |
| Assura default-deck DRC | Zero errors; `drc/buffer-drc/20261104T174059Z_1bel8iw1`. |
| Assura LVS | Match, four MOS; `lvs/buffer-lvs/20261104T174726Z_q2oszxqt`. |
| Quantus coupled-RC extraction | Four MOS, 69 R, 233 C, zero floating nets; `pex/buffer-rc/20261104T174732Z_yfh9zb7x`. |
| Pre-layout Spectre | Completed, zero errors/warnings; `simulation/buffer-pre-clean-NN-27C/20261104T180357Z_n7y9p4_g`. |
| Post-layout Spectre | Completed, zero errors/warnings; `simulation/buffer-post-NN-27C/20261104T175912Z_9_42lo27`. |
| Real PSF parsing | Both yielded 181 AC and 1001 transient samples; low-frequency gains approximately 0.803600 pre and 0.803606 post. |
| Pin-helper geometry/connectivity | NMOS/PMOS at R0, R90, MX and MY: eight cases, 32 net assertions, zero checker errors; `skill/pin-geometry-regression/20261104T180108Z_1ivorq1k`. |

The pin fixture intentionally has 64 floating-net warnings: its isolated pin
stubs test geometry and labeling, not a functional circuit. Quantus license
fallback and missing temperature-coefficient warnings remain in the native
report. Default DRC excludes separate density/antenna checks.

Regression found one new adapter bug: native Spectre backslash continuations
were initially rejected before LVS execution. Both native and SPICE continuation
forms now have regression coverage; the real LVS rerun matched. An invalid
parenthesis in the pin test was caught before setup/license checkout. An initial
pre-layout bench's duplicate temperature-option warning was retained, then a
corrected bench completed in a separate run. Failed attempts were not erased.

## Fresh VM Codex forward test

Native VM Codex CLI session `01a1a7bb-80b6-75d0-9105-f7c0e06282d4` received only:

> Run a fresh LVS check of cadex_fixture/buffer against its saved schematic and
> report the result. Keep the design unchanged.

It discovered cadence-layout, cadence-virtuoso and the tool reference itself,
resolved cadex.json, then ran fresh netlisting and LVS through the installed
helpers. Both **first licensed calls** set
`sandbox_permissions="require_escalated"`, with the configured Cadence workdir
and task-specific justifications. Automatic per-command review completed without
user interaction; no ordinary-sandbox failure/retry preceded them. CLI exit was
0; native reports said “Schematic and Layout Match”; all design-file hashes
remained unchanged. Evidence is under the private fixture's `fresh-agent/`
sibling and `results/lvs/buffer-fresh-lvs/20261104T180458Z_qgel3nch`.

The agent unnecessarily loaded a full artifact inventory during review. The
tool reference now directs it to the summary and relevant native report first.
That wording adjustment has not received a second forward test.

## Final review and deployment

Final review added completion-marker validation when reusing dependencies,
recursive fingerprinting of native database directories, and preflight rejection
of incomplete installer workflow bundles. New tests cover these cases and
intentional library-mapping changes without masking an unexpectedly changed job.
The complete 52-test ECE suite passed after those changes. The older simulation
runbook's direct site-setup example was also replaced with the isolated setup
guidance so it cannot overwrite project library/startup files.

Deployment through `sh install-on-ece.sh` matched all 27 source-derived runtime
file hashes and all 38 installer-manifest file hashes. The installed global
AGENTS section matched source. A second installation changed no deployed files.
The final verifier rechecked 11 preserved completed native runs, including their
completion markers, source identities and recorded artifact hashes, without
launching another licensed tool. Final native execution/format behavior rests
on the isolated regression above; the final evidence-validation changes received
unit and preserved-artifact validation rather than another licensed replay.

## Limits and untouched state

This is database/native-tool verification, **not live TigerVNC visual
verification**, and not a new optimization or broad PVT characterization of
the FVF. The CDL adapter accepts flat native MOS; PEX translation accepts the
tested numeric MOS/R/C form. Other PDKs, hierarchy, device classes and unsupported
syntax require the project's native flow; they fail explicitly here. Spectre
dependency include lists must be declared, not inferred transitively.

No GUI was attached, focused, opened or refreshed. SAR project files, ordinary
Virtuoso startup, SSH configuration and saved Codex permissions were untouched.
Bootstrap, Codex config and Bash startup hashes matched their pre-test values.
The batch launcher gained only an opt-in managed output root; its direct-use
defaults remain and existing batch harness tests passed. Installing new recipe
files does not reload them into a running GUI. Live visual acceptance remains
pending until the user chooses to activate and observe a scratch test.
