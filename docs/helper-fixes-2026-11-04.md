# Helper fixes after the fresh VM evaluation

The native editing failures were mostly avoidable mechanics. These changes put
bounded operations in code and keep detailed guidance in the existing live-job
reference; the top-level skill, role statement and discovery structure are unchanged.

## Changes

- `cadexMoveFigures` validates an explicit local group before mutation, removes
  duplicates and moves only ownership roots. Attached labels follow their wire
  once. The agent still chooses which local grounds/wires belong to the move;
  shared-net routing is not inferred.
- `cadexStretchWire` edits a single axis-aligned segment in place, preserving its
  identity, labels, label orientation and fractional anchors. Unsupported routing
  or attached geometry is refused before mutation. `cadexDeleteWire` refuses
  attached figures instead of deleting their labels silently.
- `cadexParam` uses the real `analogLib/vdc` CDF parameter `vdc` (with `dc` as an
  alias only for that master). Its verified callback-free string path preserves
  expressions and units. Other device parameters retain CDF callbacks; there is
  no generic arbitrary-property fallback. PDK parameter discovery remains necessary.
- Managed jobs fit a newly opened target editor and request redraw, including
  inspection. Existing editor zoom/focus is preserved. This requests presentation;
  it does not turn database completion into proof of a user's display contents.
- API/checker errors no longer suggest loading the bootstrap into an already
  connected GUI. Missing connections still return the attach command. Managed
  failures redact the session nonce. `--session` works before or after an operation.
- Native netlisting accepts zero-port top-level testbenches. Malformed port names
  remain rejected; LVS's separate interface requirements are unchanged.

## Independent validation

ECE evidence stays outside working Cadence projects:

```text
~/.local/state/cadex/helper-tests/native_xh4l9m95/
```

All 54 unlicensed tests passed, including installer/reinstaller temporary homes,
wrong/stale/ambiguous sessions, identity/serialization, session-option placement,
error handling, token redaction and zero-port netlist completion. The opt-in native
fixtures are maintained under `tests/native/`; the seed refuses an existing library.

Real IC618 batch tests passed on scratch OA databases: a source/ground/wire/label
group moved correctly even with duplicate and child selections; invalid selections
and diagonal stretches made no edit; attached-label deletion was refused; stretching
retained the label and anchor. Schematic check/save passed. Independent native
Spectre netlisting produced `VBIAS (BIAS 0) vsource dc=0.7`, VOUT dc=1.0 and MOS
width 12u with source/bulk at simulator ground. This tests effective values, not
merely the presence of a stored property.

One licensed private GUI test used authenticated Xvfb, scratch copies and a
separate temporary-home registry. Cadence's license utility reported 55/4200
framework licenses used; host memory had ample capacity. I inspected private-display
captures: both newly opened target schematics painted without an extra evaluator
refresh. A custom viewport remained identical through later inspections. Fresh
clients reconnected to the same GUI identity. This verifies the private display,
not TigerVNC or the user's working session.

A fresh actual VM Codex session received only:

> In eval_ic/bias_demo/schematic, set VBIAS to 0.65 V and move it down slightly. Check and save it.

Project context identified only the authorized disposable GUI/registry and normal
project paths. The agent discovered installed instructions, used `cadexParam`,
`cadexMoveFigures` and `cadexStretchWire`, declared connectivity expectations and
saved with zero errors/warnings. It completed in 76.5 seconds with 11 shell calls,
two nonzero: session-option placement and missing bare `python`. No follow-up or
user interaction was needed. The rollout confirms all live helper calls requested
`require_escalated`, including the first. Per-command review and saved permissions
were left in place. This is one forward sample, not a reliability/benchmark claim.

A separate batch process reopened the saved result after the private GUI stopped.
It confirmed the native 0.65 V deck, -0.25 source/ground translation, all ten pins
on wires, unchanged terminal/net maps, no instance overlap, unchanged M0/VOUT/G1
and untouched neighboring schematic. The upper named-net labels stayed stationary
as the source wire stretched. Session-option compatibility was added after this
forward sample and tested through installed fixture clients; the Python environment
was left unchanged. New GUI opening/redraw was separately tested before the agent.

Only seven authorized runtime/reference files changed among 41 protected installed
files; source/deployment comparisons matched. Global AGENTS, Codex settings,
bootstrap, batch launcher and shell startup retained their hashes. The ordinary
batch smoke passed with status 0, completion/smoke markers and 12 libraries. Private
GUI/server identities and their X display were removed. No working user GUI,
cellview, lock or TigerVNC display was contacted.

## What remains

The original [evaluation](workflow-evaluation-2026-11-04.md) and scorecard now carry
an explicit correction: revision-1 source-voltage checks were false positives
because the oracle accepted unused `dc` properties. VAMS and mirror DRC/LVS evidence
are unaffected. Corrected fixtures use `vdc` and `gnd!`.

The VAMS evaluation used **Xcelium 23.09-s003**, not 24.09. Its first ordinary
sandbox version probe died with a bad syscall; reviewed execution succeeded.
`$fatal` was a separate selected-language-mode issue. This patch does not change
Xcelium, startup or the execution environment. A contained Xcelium runner and more
precise native SKILL/checker diagnostics remain separate improvements. Rotated
geometries, shared buses, hierarchical designs and additional PDK parameters still
need broader coverage. Live visual verification on the user's TigerVNC is pending.
