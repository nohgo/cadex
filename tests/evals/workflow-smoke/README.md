# Native workflow evaluation inputs

These are evaluation inputs and a sanitized observation record, not installed
agent instructions or an automatically run test suite. See
[the report](../../../docs/workflow-evaluation-2026-11-04.md) for methodology,
limitations, private evidence paths and recommendations.

- `cases.json`: the short requests and independent acceptance criteria.
- `fixtures/dac6_rnm.vams` and `dac6-contract.md`: a deliberately defective
  wreal DAC and its intended contract. The missing reference sensitivity is
  intentional; a good bench should fail it while leaving it unchanged.
- `fixtures/designs.json`: evaluator-created schematic fixture specifications.
  Existing user libraries are not fixtures and must not be used as substitutes.
- `2026-11-04-results.json`: public metrics and independent checks; no session
  nonces, raw RPC logs, PDK code, compiled databases or saved permissions.

Reproduction requires explicit licensed execution on ECE. Create fresh disposable
projects and establish their normal launch/library context before giving a fresh
VM Codex session the corresponding request. Keep desired answers and independent
checks out of the candidate prompt. The live case needs its own private GUI,
display, registry and explicit session authorization; existing sessions are never
implicitly authorized. Keep normal per-command review, and clean up only the
process identities created for the test.

The original evaluation's complete orchestration scripts and native artifacts
remain in its private ECE evidence root. These portable inputs do not constitute
a one-command native benchmark runner. Run source-fixture tests separately from
licensed end-to-end evaluation. Do not claim a reliability rate from one run per
case or merge a corrected model into the intentionally defective fixture.
